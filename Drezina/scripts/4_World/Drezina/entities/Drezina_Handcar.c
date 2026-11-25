// Дрезина. Движется по пути скриптом (без физики машины):
//  - сервер считает дистанцию по пути и скорость, синхронизирует их;
//  - каждый клиент сам строит ту же геометрию пути и плавно ставит дрезину на нужную дистанцию;
//  - водитель стоит на платформе через DrezinaRideCommand (HumanCommandScript).

class Drezina_Handcar extends ItemBase
{
	static const float DECK_HEIGHT   = 0.67;  // где стоит водитель: пол платформы 0.62 + 5 см (не цеплять коллизию платформы)
	static const float SEAT_BACK     = 0.80;  // насколько водитель стоит за рычагом (по ходу)
	static const float WHEEL_RADIUS  = 0.36;

	// --- синхронизируемое состояние
	int   m_TrackId;
	float m_SyncDist;
	float m_SyncSpeed;
	int   m_Dir = 1;        // 1 — по росту дистанции, -1 — обратно
	bool  m_Pumping;
	bool  m_Braking;
	int   m_DriverLow;
	int   m_DriverHigh;

	// пока на дрезине едет местный водитель, её двигает его команда езды (в одной фазе кадра
	// с персонажем, иначе камера дрожит); общий цикл обновления такую дрезину пропускает
	bool m_TickedByRide;

	// клиент водителя сам считает разгон от своих нажатий (как сервер), чтобы не ждать сервер
	int   m_LocalThrottle;
	float m_PredSpeed;

	// сервер: когда последний раз переставляли модель
	float m_ServerXformTimer;
	bool  m_ServerXformStopped;

	// --- локальное состояние (сервер и клиент)
	float m_Dist;
	float m_Speed;
	PlayerBase m_Driver;

	// --- только сервер
	int   m_Throttle;       // -1 / 0 / 1
	float m_IdleTime;
	float m_SyncTimer;

	// --- только клиент (анимация)
	float m_LeverT;
	float m_WheelPhase;
	float m_PredDist;       // последняя серверная дистанция, продвинутая вперёд по скорости

	// --- только клиент (звук)
	static const float RAIL_JOINT_STEP = 12.5;  // стыки рельсов через 12.5 м, как на настоящей дороге
	static const float AXLE_SPACING    = 1.24;  // между осями дрезины
	Drezina_HeadLight m_LightFront;
	Drezina_HeadLight m_LightBack;
	Drezina_BulbLight m_LightBulb;
	EffectSound m_SndDynamo;
	EffectSound m_SndRoll;
	EffectSound m_SndBrake;
	float m_JointAccum;
	float m_SecondClackIn = -1;
	float m_PrevLeverCos = 1;
	float m_RandomCreakTimer;

	void Drezina_Handcar()
	{
		RegisterNetSyncVariableInt("m_TrackId");
		RegisterNetSyncVariableFloat("m_SyncDist", 0, 200000, 2);
		RegisterNetSyncVariableFloat("m_SyncSpeed", 0, 100, 2);
		RegisterNetSyncVariableInt("m_Dir", -1, 1);
		RegisterNetSyncVariableBool("m_Pumping");
		RegisterNetSyncVariableBool("m_Braking");
		RegisterNetSyncVariableInt("m_DriverLow");
		RegisterNetSyncVariableInt("m_DriverHigh");

		DrezinaTrackManager.Get().RegisterHandcar(this);
	}

	void ~Drezina_Handcar()
	{
		if (DrezinaTrackManager.s_Instance)
			DrezinaTrackManager.s_Instance.UnregisterHandcar(this);
	}

	override void EEInit()
	{
		super.EEInit();
		NoCharacterCollision();
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(NoCharacterCollision, 500, false);
	}

	// персонаж не сталкивается с дрезиной (иначе физика выталкивает водителя, а дрезину трясёт)
	void NoCharacterCollision()
	{
		if (dBodyIsSet(this))
		{
			dBodySetInteractionLayer(this, PhxInteractionLayers.ITEM_SMALL);
			Print("[Drezina] handcar: коллизия с персонажем отключена");
		}
	}

	override void EEDelete(EntityAI parent)
	{
		super.EEDelete(parent);
		DestroyLights();
		StopLoop(m_SndDynamo);
		StopLoop(m_SndRoll);
		StopLoop(m_SndBrake);
		m_SndRoll = null;
		m_SndBrake = null;
		if (m_Driver && m_Driver.m_DrezinaHandcar == this)
			m_Driver.m_DrezinaHandcar = null;
		DrezinaTrackManager.Get().UnregisterHandcar(this);
	}

	// --- в инвентарь не берётся
	override bool CanPutInCargo(EntityAI parent)
	{
		return false;
	}

	override bool CanPutIntoHands(EntityAI parent)
	{
		return false;
	}

	override bool DisableVicinityIcon()
	{
		return true;
	}

	bool HasDriver()
	{
		return m_DriverLow != 0 || m_DriverHigh != 0;
	}

	DrezinaTrack GetTrack()
	{
		return DrezinaTrackManager.Get().GetTrack(m_TrackId);
	}

	// ------------------------------------------------------------------ сервер

	void ServerPlaceOnTrack(int trackId, float dist, int dir)
	{
		m_TrackId = trackId;
		m_Dist = dist;
		m_Speed = 0;
		m_Dir = dir;
		if (m_Dir == 0)
			m_Dir = 1;
		m_SyncDist = m_Dist;
		m_SyncSpeed = 0;
		ApplyTransform();
		SetSynchDirty();
	}

	void ServerSetDriver(PlayerBase player)
	{
		ServerClearDriver();
		if (!player)
			return;
		m_Driver = player;
		player.m_DrezinaHandcar = this;
		player.GetNetworkID(m_DriverLow, m_DriverHigh);
		m_Throttle = 0;
		m_IdleTime = 0;
		SetSynchDirty();
		Print("[Drezina] водитель назначен, путь #" + m_TrackId + ", дистанция " + m_Dist);
		DrezinaTrackManager.Notify(player.GetIdentity(), HelpText());
	}

	void ServerClearDriver()
	{
		if (m_Driver && m_Driver.m_DrezinaHandcar == this)
			m_Driver.m_DrezinaHandcar = null;
		m_Driver = null;
		m_DriverLow = 0;
		m_DriverHigh = 0;
		m_Throttle = 0;
		m_Pumping = false;
		m_Braking = false;
		SetSynchDirty();
	}

	bool DriverFarFromSeat()
	{
		vector seat;
		float yaw;
		GetDriverTransform(seat, yaw);
		return vector.Distance(m_Driver.GetPosition(), seat) > 6.0;
	}

	bool IsSenderDriver(PlayerIdentity sender)
	{
		if (!sender || !m_Driver || !m_Driver.GetIdentity())
			return false;
		return m_Driver.GetIdentity().GetId() == sender.GetId();
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);
		if (!GetGame().IsServer())
			return;

		if (rpc_type == DrezinaRPC.HC_THROTTLE)
		{
			Param1<int> p = new Param1<int>(0);
			bool okRead = ctx.Read(p);
			if (okRead && IsSenderDriver(sender))
				m_Throttle = Math.Clamp(p.param1, -1, 1);
			Print("[Drezina] throttle " + p.param1 + " driver=" + IsSenderDriver(sender));
		}
		else if (rpc_type == DrezinaRPC.HC_REVERSE)
		{
			if (IsSenderDriver(sender))
			{
				if (m_Speed <= DrezinaSettings.Get().ReverseMaxSpeed)
				{
					m_Dir = -m_Dir;
					m_Speed = 0;
					SetSynchDirty();
					DrezinaTrackManager.Notify(sender, "Направление сменено.");
				}
				else
				{
					DrezinaTrackManager.Notify(sender, "Сначала остановитесь (S).");
				}
			}
		}
		else if (rpc_type == DrezinaRPC.HC_LEAVE)
		{
			if (IsSenderDriver(sender))
			{
				PlayerBase leaving = m_Driver;
				ServerClearDriver();
				if (leaving)
				{
					// поставить рядом с дрезиной, а не на платформе
					vector side = Vector(GetDirection()[2], 0, -GetDirection()[0]).Normalized();
					vector off = GetPosition() + side * 1.3;
					off[1] = GetPosition()[1] + 0.05;
					leaving.SetPosition(off);
					leaving.m_DrezinaLeftTime = GetGame().GetTime();
					Print("[Drezina] водитель сошёл");
				}
			}
		}
	}

	void ServerSimulate(float dt)
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return;

		DrezinaSettings st = DrezinaSettings.Get();

		// водитель пропал / умер / отошёл
		if (HasDriver())
		{
			if (!m_Driver || !m_Driver.IsAlive() || m_Driver.IsUnconscious() || !m_Driver.GetIdentity() || DriverFarFromSeat())
				ServerClearDriver();
		}

		if (!HasDriver())
		{
			m_Throttle = 0;
			m_IdleTime += dt;
			if (m_IdleTime > st.AbandonSeconds && m_Speed < 0.01)
			{
				GetGame().ObjectDelete(this);
				return;
			}
		}
		else
		{
			m_IdleTime = 0;
		}

		m_Speed = Math.Clamp(m_Speed + Accel(t, m_Throttle) * dt, 0, st.MaxSpeed);

		float newDist = m_Dist + m_Speed * m_Dir * dt;
		if (DrezinaTrackManager.Get().IsBlocked(this, newDist))
		{
			m_Speed = 0;
			newDist = m_Dist;
		}
		if (newDist <= 0 || newDist >= t.GetLength())
		{
			newDist = Math.Clamp(newDist, 0, t.GetLength());
			m_Speed = 0;
		}
		m_Dist = newDist;

		bool pumping = m_Throttle > 0;
		bool braking = m_Throttle < 0 && m_Speed > 0.3;
		// модель на сервере двигаем редко: раз в 2 с на ходу и при остановке. Каждое такое
		// перемещение пересылается клиентам, а они двигают дрезину сами и плавно.
		m_ServerXformTimer += dt;
		bool stopped = m_Speed < 0.01;
		if (m_ServerXformTimer >= 2.0 || (stopped && !m_ServerXformStopped))
		{
			m_ServerXformTimer = 0;
			ApplyTransform();
		}
		m_ServerXformStopped = stopped;

		// синхронизация ~10 раз в секунду или при смене состояния
		m_SyncTimer += dt;
		float syncEvery = 0.25;
		if (m_Speed > 0.05)
			syncEvery = 0.05;   // на ходу 20 раз в секунду: клиент держит дрезину там же, где сервер
		if (m_SyncTimer >= syncEvery || pumping != m_Pumping || braking != m_Braking)
		{
			m_SyncTimer = 0;
			m_Pumping = pumping;
			m_Braking = braking;
			m_SyncDist = m_Dist;
			m_SyncSpeed = m_Speed;
			SetSynchDirty();
		}
	}

	// ------------------------------------------------------------------ клиент

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();

		// водитель
		PlayerBase newDriver = null;
		if (HasDriver())
			newDriver = PlayerBase.Cast(GetGame().GetObjectByNetworkId(m_DriverLow, m_DriverHigh));
		if (newDriver != m_Driver)
		{
			if (m_Driver && m_Driver.m_DrezinaHandcar == this)
				m_Driver.m_DrezinaHandcar = null;
			m_Driver = newDriver;
			if (m_Driver)
			{
				m_Driver.m_DrezinaHandcar = this;
				if (m_Driver == GetGame().GetPlayer())
					DrezinaClientInput.OnBoarded(this);
			}
		}

		// дистанция: маленькое расхождение сглаживаем, большое — прыжок
		m_PredDist = m_SyncDist;
		m_PredSpeed = m_SyncSpeed;
		if (IsLocalDriver())
		{
			// своя дрезина считается локально; прыжок — только при большом расхождении
			if (Math.AbsFloat(m_SyncDist - m_Dist) > 3.0)
			{
				m_Dist = m_SyncDist;
				m_Speed = m_SyncSpeed;
			}
		}
		else
		{
			if (Math.AbsFloat(m_SyncDist - m_Dist) > 1.5)
				m_Dist = m_SyncDist;
			m_Speed = m_SyncSpeed;
		}
	}

	// ускорение от рычага/тормоза, трения и уклона — одинаково на сервере и у клиента водителя
	float Accel(DrezinaTrack t, int throttle)
	{
		DrezinaSettings st = DrezinaSettings.Get();
		vector pos, dir;
		t.GetPosDir(m_Dist, pos, dir);
		float accel = -st.RollingFriction;
		if (throttle > 0)
			accel += st.PumpAcceleration;
		else if (throttle < 0)
			accel -= st.BrakeDeceleration;
		// уклон: dir[1] — вертикальная составляющая направления пути
		accel -= st.SlopeFactor * dir[1] * m_Dir;
		return accel;
	}

	bool IsLocalDriver()
	{
		return !GetGame().IsDedicatedServer() && m_Driver && m_Driver == GetGame().GetPlayer();
	}

	void ClientSimulate(float dt)
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return; // геометрии ещё нет — положение придёт от сервера

		if (IsLocalDriver())
		{
			// своя дрезина: разгон считаем сами от нажатий, без задержки сети
			m_Speed = Math.Clamp(m_Speed + Accel(t, m_LocalThrottle) * dt, 0, DrezinaSettings.Get().MaxSpeed);
			float newDist = m_Dist + m_Speed * m_Dir * dt;
			if (newDist <= 0 || newDist >= t.GetLength())
			{
				newDist = Math.Clamp(newDist, 0, t.GetLength());
				m_Speed = 0;
			}
			m_Dist = newDist;
			// с сервером сверяемся мягко: тянем, только если разошлись больше чем на 1 м
			m_PredDist = Math.Clamp(m_PredDist + m_PredSpeed * m_Dir * dt, 0, t.GetLength());
			float err = m_PredDist - m_Dist;
			if (m_LocalThrottle == 0 && m_PredSpeed < 0.05 && m_Speed < 0.3)
			{
				// стоим: точно встаём туда же, где дрезина на сервере, иначе сервер тянет
				// персонажа к своей точке, а мы к своей — отсюда дрожь на месте
				m_Dist += err * Math.Clamp(dt * 8.0, 0, 1);
				if (m_PredSpeed < 0.05)
					m_Speed = m_Speed * Math.Clamp(1 - dt * 4.0, 0, 1);
			}
			else if (Math.AbsFloat(err) > 1.0)
				m_Dist += err * Math.Clamp(dt * 2.0, 0, 1);
			else
				m_Dist += err * Math.Clamp(dt * 0.7, 0, 1);
			ApplyTransform();
			return;
		}

		float step = m_Speed * m_Dir * dt;
		m_PredDist = Math.Clamp(m_PredDist + step, 0, t.GetLength());
		m_Dist += step;
		m_Dist += (m_PredDist - m_Dist) * Math.Clamp(dt * 20.0, 0, 1);
		m_Dist = Math.Clamp(m_Dist, 0, t.GetLength());
		ApplyTransform();
	}

	// Анимация колёс и рычага (всё, что не на выделенном сервере).
	void UpdateAnimation(float dt)
	{
		// колёса
		float turns = m_Speed * dt / (Math.PI2 * WHEEL_RADIUS);
		m_WheelPhase += turns * m_Dir;
		m_WheelPhase -= Math.Floor(m_WheelPhase);
		SetAnimationPhase("drezina_wheels", m_WheelPhase);

		// коромысло: частота качания зависит от скорости; если качают на месте — минимальная частота
		float leverRate = m_Speed * 1.1;
		if (m_Pumping && leverRate < 2.5)
			leverRate = 2.5;
		m_LeverT += leverRate * dt;
		if (m_LeverT > Math.PI2)
			m_LeverT -= Math.PI2;
		if (leverRate > 0.01)
			SetAnimationPhase("drezina_lever", 0.5 + 0.5 * Math.Sin(m_LeverT));

		UpdateSounds(dt, leverRate);
		UpdateLights(dt);
	}

	// Самодельный свет от динамо-машины на колесе: чем быстрее едешь, тем ярче.
	// На малой скорости генератор «не тянет» — свет тусклый и мигает. Встал — погасло.
	static const float LIGHT_ON_SPEED  = 0.35;
	static const float LIGHT_OFF_SPEED = 0.15;
	static const float LIGHT_FULL_SPEED = 5.0;

	void UpdateLights(float dt)
	{
		bool lit = m_LightFront != null;
		if (!lit && m_Speed > LIGHT_ON_SPEED)
			CreateLights();
		else if (lit && m_Speed < LIGHT_OFF_SPEED)
			DestroyLights();
		if (!m_LightFront)
			return;

		float k = Math.Clamp(m_Speed / LIGHT_FULL_SPEED, 0, 1);
		k = Math.Pow(k, 0.7);
		if (m_Speed < 2.0)
			k *= Math.RandomFloatInclusive(0.55, 1.0);   // слабый ток — мигает
		m_LightFront.SetBrightnessTo(Drezina_HeadLight.MAX_BRIGHTNESS * k);
		m_LightBack.SetBrightnessTo(Drezina_HeadLight.MAX_BRIGHTNESS * k * 0.7);
		if (m_LightBulb)
			m_LightBulb.SetBrightnessTo(Drezina_BulbLight.MAX_BRIGHTNESS * k);

		// гул динамо
		if (!m_SndDynamo)
			m_SndDynamo = SEffectManager.PlaySoundOnObject("Drezina_Dynamo_SoundSet", this, 0.3, 0.3, true);
		if (m_SndDynamo)
			m_SndDynamo.SetSoundVolume(Math.Clamp(k, 0.2, 1.0));
	}

	void CreateLights()
	{
		m_LightFront = Drezina_HeadLight.Cast(ScriptedLightBase.CreateLight(Drezina_HeadLight, GetPosition()));
		if (m_LightFront)
			m_LightFront.AttachOnMemoryPoint(this, "light_front", "light_front_dir");
		m_LightBack = Drezina_HeadLight.Cast(ScriptedLightBase.CreateLight(Drezina_HeadLight, GetPosition()));
		if (m_LightBack)
			m_LightBack.AttachOnMemoryPoint(this, "light_back", "light_back_dir");
		m_LightBulb = Drezina_BulbLight.Cast(ScriptedLightBase.CreateLight(Drezina_BulbLight, GetPosition()));
		if (m_LightBulb)
			m_LightBulb.AttachOnMemoryPoint(this, "light_bulb");
	}

	void DestroyLights()
	{
		if (m_LightFront)
			m_LightFront.Destroy();
		if (m_LightBack)
			m_LightBack.Destroy();
		if (m_LightBulb)
			m_LightBulb.Destroy();
		m_LightFront = null;
		m_LightBack = null;
		m_LightBulb = null;
		StopLoop(m_SndDynamo);
		m_SndDynamo = null;
	}

	// ------------------------------------------------------------------ звук (клиент)

	void UpdateSounds(float dt, float leverRate)
	{
		// гул качения: громкость по скорости
		if (m_Speed > 0.3)
		{
			if (!m_SndRoll)
				m_SndRoll = SEffectManager.PlaySoundOnObject("Drezina_Roll_SoundSet", this, 0.4, 0.6, true);
			if (m_SndRoll)
				m_SndRoll.SetSoundVolume(Math.Clamp(m_Speed / 8.0, 0.15, 1.0));
		}
		else if (m_SndRoll)
		{
			StopLoop(m_SndRoll);
			m_SndRoll = null;
		}

		// «та-так» на стыках: удар передней оси, через AXLE_SPACING — задней
		if (m_Speed > 0.8)
		{
			m_JointAccum += m_Speed * dt;
			if (m_JointAccum >= RAIL_JOINT_STEP)
			{
				m_JointAccum -= RAIL_JOINT_STEP;
				PlayOneShot("Drezina_Clack_SoundSet");
				m_SecondClackIn = AXLE_SPACING / m_Speed;
			}
		}
		if (m_SecondClackIn >= 0)
		{
			m_SecondClackIn -= dt;
			if (m_SecondClackIn < 0)
				PlayOneShot("Drezina_Clack_SoundSet");
		}

		// скрип коромысла в крайних точках хода, иногда — стук рычага
		float leverCos = Math.Cos(m_LeverT);
		if (leverRate > 0.5 && (leverCos >= 0) != (m_PrevLeverCos >= 0))
		{
			if (Math.RandomFloat01() < 0.75)
				PlayOneShot("Drezina_Creak_SoundSet");
			if (m_Pumping && Math.RandomFloat01() < 0.35)
				PlayOneShot("Drezina_Knock_SoundSet");
		}
		m_PrevLeverCos = leverCos;

		// старая рама поскрипывает и накатом
		if (m_Speed > 1.0 && !m_Pumping)
		{
			m_RandomCreakTimer -= dt;
			if (m_RandomCreakTimer <= 0)
			{
				m_RandomCreakTimer = Math.RandomFloatInclusive(2.5, 7.0);
				PlayOneShot("Drezina_Creak_SoundSet");
			}
		}

		// визг колодок
		if (m_Braking && m_Speed > 0.3)
		{
			if (!m_SndBrake)
				m_SndBrake = SEffectManager.PlaySoundOnObject("Drezina_Brake_SoundSet", this, 0.1, 0.25, true);
		}
		else if (m_SndBrake)
		{
			StopLoop(m_SndBrake);
			m_SndBrake = null;
		}
	}

	void PlayOneShot(string soundSet)
	{
		EffectSound snd = SEffectManager.PlaySoundOnObject(soundSet, this);
		if (snd)
			snd.SetAutodestroy(true);
	}

	static void StopLoop(EffectSound snd)
	{
		if (!snd)
			return;
		snd.SetAutodestroy(true);
		snd.SoundStop();
	}

	// ------------------------------------------------------------------ общее

	// Вызывается каждый кадр из DrezinaTrackManager.OnUpdate (очередь обновления игры):
	// EOnFrame у предметов срабатывает не везде.
	void Tick(float timeSlice)
	{
		if (m_TrackId == 0)
			return;

		if (GetGame().IsServer())
			ServerSimulate(timeSlice);
		else
			ClientSimulate(timeSlice);

		KeepDriverOnDeck();

		if (!GetGame().IsDedicatedServer())
			UpdateAnimation(timeSlice);
	}

	void ApplyTransform()
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return;
		vector pos, dir;
		t.GetPosDir(m_Dist, pos, dir);
		pos[1] = pos[1] + DrezinaSettings.Get().RailHeightOffset;
		SetPosition(pos);
		SetDirection(dir);
	}

	// Запасная привязка водителя: если скриптовая команда езды не держит персонажа на площадке,
	// ставим его на место сами (сервер — для всех, клиент водителя — чтобы не было рывков).
	void KeepDriverOnDeck()
	{
		// только сервер и только если персонаж реально слетел (команда езды не держит его):
		// мелкие расхождения сервера и клиента нормальны, их поправлять нельзя — будут рывки
		if (!m_Driver || !HasDriver() || !GetGame().IsServer())
			return;
		vector seat;
		float yaw;
		GetDriverTransform(seat, yaw);
		if (vector.Distance(m_Driver.GetPosition(), seat) > 2.0)
		{
			m_Driver.SetPosition(seat);
			m_Driver.SetOrientation(Vector(yaw, 0, 0));
		}
	}

	// Где стоит водитель (мир) и куда смотрит (yaw в градусах).
	// Считается прямо по пути (по m_Dist), а не по модели: на сервере модель двигается
	// не каждый кадр (иначе её положение пересылается клиентам и дрезина у них дрожит).
	void GetDriverTransform(out vector pos, out float yaw)
	{
		DrezinaTrack t = GetTrack();
		if (!t)
		{
			pos = ModelToWorld(Vector(0, DECK_HEIGHT, -SEAT_BACK * m_Dir));
			yaw = GetDirection().VectorToAngles()[0];
			return;
		}
		vector tp, dir;
		t.GetPosDir(m_Dist, tp, dir);
		tp[1] = tp[1] + DrezinaSettings.Get().RailHeightOffset + DECK_HEIGHT;
		pos = tp - dir * (SEAT_BACK * m_Dir);
		vector face = dir;
		if (m_Dir < 0)
			face = dir * -1;
		yaw = face.VectorToAngles()[0];
	}

	// Текущая подсказка для HUD.
	static string HelpText()
	{
		return "W — качать рычаг, S — тормоз, R — сменить направление (на месте), F — сойти";
	}
}

// Фара от старой машины: узкий тёплый луч вдоль пути.
class Drezina_HeadLight extends SpotLightBase
{
	static const float MAX_BRIGHTNESS = 6.0;

	void Drezina_HeadLight()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(28);
		SetSpotLightAngle(75);
		SetCastShadow(true);
		SetFlareVisible(true);
		SetBrightnessTo(0);
		SetDiffuseColor(1.0, 0.82, 0.55);
		SetAmbientColor(1.0, 0.82, 0.55);
	}
}

// Голая лампочка под стойкой: освещает саму дрезину и водителя.
class Drezina_BulbLight extends PointLightBase
{
	static const float MAX_BRIGHTNESS = 1.6;

	void Drezina_BulbLight()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(5);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetBrightnessTo(0);
		SetDiffuseColor(1.0, 0.72, 0.42);
		SetAmbientColor(1.0, 0.72, 0.42);
	}
}
