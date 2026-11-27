// Мотодрезина: настоящая машина DayZ (садятся как в машину, игрок — член экипажа, никакой тряски),
// но едет только по рельсам. Мотор, бензин, свеча, аккумулятор, фары (лампочки H7) и сумка —
// ванильная механика CarScript. Колёс-запчастей у машины нет: после каждого шага физики скрипт сам
// ставит машину на путь и задаёт ей скорость вдоль рельсов (газ/тормоз/передачи берутся у машины).
//
// Места: 0 — водитель (в центре, лицом вперёд), 1 и 2 — пассажиры сзади слева/справа (лицом наружу).
// Состояние дрезины для сетевого отката машин (как m_fTime у ванильной машины). Машина водителя
// считается наперёд; пришла поправка сервера — игра откатывает её к состоянию сервера и заново
// прокручивает ввод. Наш путь/сторона/стрелка должны откатываться вместе с положением, иначе после
// каждой поправки дрезина считалась по чужому пути — рывки назад и дребезг прицепа.
class Drezina_MotorOwnerState : CarScriptOwnerState
{
	// всё во float: ванильное состояние пишет только float (номера путей float хранит точно)
	float m_dTrack;
	float m_dFace;
	float m_dPrevTrack;
	float m_dPrevD;
	float m_dPrevMove;
	float m_dPrevFace;
	float m_dEntryD;
	float m_dSince;
	float m_dHint;

	protected override event void Write(PawnStateWriter ctx)
	{
		super.Write(ctx);
		ctx.Write(m_dTrack);
		ctx.Write(m_dFace);
		ctx.Write(m_dPrevTrack);
		ctx.Write(m_dPrevD);
		ctx.Write(m_dPrevMove);
		ctx.Write(m_dPrevFace);
		ctx.Write(m_dEntryD);
		ctx.Write(m_dSince);
		ctx.Write(m_dHint);
	}

	protected override event void Read(PawnStateReader ctx)
	{
		super.Read(ctx);
		ctx.Read(m_dTrack);
		ctx.Read(m_dFace);
		ctx.Read(m_dPrevTrack);
		ctx.Read(m_dPrevD);
		ctx.Read(m_dPrevMove);
		ctx.Read(m_dPrevFace);
		ctx.Read(m_dEntryD);
		ctx.Read(m_dSince);
		ctx.Read(m_dHint);
	}
};

class Drezina_Motor extends CarScript
{
	static ref array<Drezina_Motor> s_All = new array<Drezina_Motor>;

	static const float WHEEL_RADIUS = 0.36;
	static const float ACCEL = 2.2;          // м/с² при полном газе
	static const float BRAKE_DECEL = 5.0;
	static const float ROLL_DECEL = 0.25;    // накат без газа
	static const float HANDBRAKE_DECEL = 7.0;
	static const float HOVER = 0.05;
	static const float END_GAP = 1.6;
	static const float MAX_SPEED = 13.9;     // 50 км/ч         // физические колёса не касаются рельсов: нет сил подвески — нет дрожи

	int m_TrackId = -1;
	int m_Face = 1;              // +1 — нос машины смотрит в сторону роста дистанции пути
	float m_DistHint = -1;       // последняя дистанция по пути (для быстрого поиска проекции)
	float m_WheelPhase;
	int m_LastFrameTime;
	float m_LogTimer;
	bool m_GravityOff;
	bool m_Sleeping;
	float m_StillTime;
	bool m_OffRail;              // снята с рельсов (стоит рядом с путём, чтобы разъехаться со встречной)
	int m_TrailerType;           // прицеп — часть мотодрезины: 0 нет, 1 пассажирский, 2 грузовой
	// последний переход на стрелке (для прицепа: сразу после стрелки он ещё на прежнем пути)
	int m_PrevTrack;
	float m_PrevD;
	int m_PrevMove;
	int m_PrevFace;
	float m_EntryD;
	int m_TransferTime = -100000;
	float m_SinceTransfer = 100;  // путь, пройденный после последней стрелки (м)
	// клиент водителя: свой переход важнее устаревшей синхронизации с сервера
	int m_LTrack;
	int m_LFace;
	int m_LPrevTrack;
	float m_LPrevD;
	int m_LPrevMove;
	int m_LPrevFace;
	float m_LEntryD;

	static const float TRAILER_GAP = 2.9;   // между центрами мотодрезины и прицепа (прицеп сзади)

	void Drezina_Motor()
	{
		RegisterNetSyncVariableInt("m_TrackId");
		RegisterNetSyncVariableInt("m_Face", -1, 1);
		RegisterNetSyncVariableBool("m_OffRail");
		RegisterNetSyncVariableInt("m_TrailerType", 0, 2);
		RegisterNetSyncVariableInt("m_PrevTrack");
		RegisterNetSyncVariableFloat("m_PrevD", 0, 100000, 2);
		RegisterNetSyncVariableInt("m_PrevMove", -1, 1);
		RegisterNetSyncVariableInt("m_PrevFace", -1, 1);
		RegisterNetSyncVariableFloat("m_EntryD", 0, 100000, 2);

		m_EngineStartOK = "Motorbike_01_engine_start_SoundSet";
		m_EngineStartBattery = "";
		m_EngineStartPlug = "";
		m_EngineStartFuel = "Motorbike_01_engine_failed_start_fuel_SoundSet";
		m_EngineStop = "Motorbike_01_engine_stop_SoundSet";
		m_EngineStopFuel = "Motorbike_01_engine_stop_fuel_SoundSet";

		// фары: свет как у ванильного мотоцикла (у базового профиля машины нет яркости)
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Drezina_MotorLightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Motorbike_01LightProfileRear()));

		// мотор справа впереди (координаты модели: x вправо, y вверх, z вперёд)
		SetEnginePos("0.22 0.82 0.72");
		s_All.Insert(this);
		GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(WakeWatch);
		if (!GetGame().IsDedicatedServer())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(LanternTick);
	}

	void ~Drezina_Motor()
	{
		if (GetGame())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Remove(WakeWatch);
		if (GetGame())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Remove(LanternTick);
		if (m_Lantern)
			m_Lantern.Destroy();
		DestroyTrailerVis();
		if (s_All)
			s_All.RemoveItem(this);
	}

	// ------------------------------------------------------------------ сохранение (путь и сторона)

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(m_TrackId);
		ctx.Write(m_Face);
		ctx.Write(m_OffRail);
		ctx.Write(m_TrailerType);
	}

	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;
		if (!ctx.Read(m_TrackId))
			m_TrackId = -1;
		if (!ctx.Read(m_Face))
			m_Face = 1;
		if (!ctx.Read(m_OffRail))
			m_OffRail = false;
		if (!ctx.Read(m_TrailerType) || m_TrailerType < 0 || m_TrailerType > 2)
			m_TrailerType = 0;      // в старых сохранениях тут номер сцепки отдельного прицепа
		return true;
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		SetSynchDirty();
	}

	// ------------------------------------------------------------------ экипаж и посадка

	// посадка как в машине (анимации Нивы); все трое смотрят вперёд
	override int GetAnimInstance()
	{
		return VehicleAnimInstances.HATCHBACK;
	}

	override int GetSeatAnimationType(int posIdx)
	{
		switch (posIdx)
		{
			case 0:
				return DayZPlayerConstants.VEHICLESEAT_DRIVER;
			// пассажиры садятся как передний пассажир (шаг вбок на сиденье, без «нырка» назад, как на заднее
			// сиденье Нивы). Анимация рассчитана на вход справа: правый садится снаружи, левый — с пола в центре.
			case 1:
			case 2:
				return DayZPlayerConstants.VEHICLESEAT_CODRIVER;
		}
		return 0;
	}

	override bool CrewCanGetThrough(int posIdx)
	{
		return !m_OffRail;   // дверей нет; снятую с рельсов сначала ставят обратно
	}

	// места 3..6 — пассажирский прицеп: только когда он прицеплен
	override bool CanReachSeatFromSeat(int currentSeat, int nextSeat)
	{
		if (nextSeat >= 3 && m_TrailerType != 1)
			return false;
		return true;
	}

	override bool CanReachSeatFromDoors(string pSeatSelection, vector pFromPos, float pDistance = 1.0)
	{
		if (pSeatSelection.IndexOf("seat_cargo") == 0)
		{
			int n = pSeatSelection.Substring(10, pSeatSelection.Length() - 10).ToInt();
			if (n >= 3)
			{
				if (m_TrailerType != 1)
					return false;
				string pos = "pos_cargo" + n;
				if (!MemoryPointExists(pos))
					return false;
				vector ws = ModelToWorld(GetMemoryPointPos(pos));
				ws[1] = 0;
				pFromPos[1] = 0;
				return vector.Distance(pFromPos, ws) <= 1.6;
			}
		}
		return super.CanReachSeatFromDoors(pSeatSelection, pFromPos, pDistance);
	}

	override bool CanReachDoorsFromSeat(string pDoorsSelection, int pCurrentSeat)
	{
		return true;
	}

	override float GetTransportCameraDistance()
	{
		return 3.5;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 1.6 0";
	}

	// ------------------------------------------------------------------ что нужно мотору

	override bool IsVitalRadiator()
	{
		return false;
	}

	override bool IsVitalEngineBelt()
	{
		return false;
	}

	override bool IsVitalGlowPlug()
	{
		return false;
	}

	// аккумулятор не нужен: заводится свечой и бензином, фары горят от генератора при работающем моторе
	override bool NeedElectricitySourceDevice()
	{
		return false;
	}

	// спящую физику будим, когда водитель газует или переключил передачу при заведённом моторе
	void WakeWatch(float dt)
	{
		if (!m_Sleeping)
			return;
		if (!GetGame().IsServer() && !IsOwner())
			return;
		if (!CrewDriver())
			return;
		// водитель сел — будим сразу (а не по газу): иначе сервер и клиент трогались в разные кадры
		// и серверная копия уезжала на десятки метров
		if (CrewDriver())
		{
			m_Sleeping = false;
			m_StillTime = 0;
			dBodyActive(this, ActiveState.ACTIVE);
		}
	}

	override bool IsVitalSparkPlug()
	{
		return true;
	}

	// колёса (ванильные колёса Нивы, невидимые: в модели свои колёса) — только для физики машины, снимать нельзя
	static bool IsWheelSlot(string slot)
	{
		return slot.IndexOf("NivaWheel_") == 0;
	}

	override bool CanReleaseAttachment(EntityAI attachment)
	{
		if (attachment)
		{
			InventoryLocation il = new InventoryLocation;
			attachment.GetInventory().GetCurrentInventoryLocation(il);
			if (IsWheelSlot(InventorySlots.GetSlotName(il.GetSlot())))
				return false;
		}
		return super.CanReleaseAttachment(attachment);
	}

	void ServerFitWheels()
	{
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
	}

	// без «Толкать» (толчок физикой дёргает машину, а по рельсам её всё равно держит скрипт)
	override void SetActions()
	{
		AddAction(ActionGetInTransport);
		AddAction(ActionDrezinaTurnAround);
		AddAction(ActionDrezinaOffRail);
		AddAction(ActionDrezinaOnRail);
		// действие фар должно быть у любой машины: без него ванильный ввод падал с ошибкой каждый кадр,
		// пока сидишь в дрезине (жуткие лаги и прыжки). Фары разбиты: свет у профиля нулевой.
		AddAction(ActionSwitchLights);
		AddAction(ActionVehicleHornShort);
		AddAction(ActionVehicleHornLong);
	}

	// аккумулятора нет (как у ванильного мотоцикла) — фары включаются без него.
	// Базовая машина требует аккумулятор, поэтому раньше работал только стоп-сигнал.
	override bool OnBeforeLightOn()
	{
		return true;   // только стоп-сигнал: фары разбиты, включателя нет
	}

	// почему не заводится — в лог
	override bool OnBeforeEngineStart()
	{
		bool ok = super.OnBeforeEngineStart();
		int state = CheckOperationalRequirements();
		string bat = "нет";
		ItemBase b = GetBattery();
		if (b && b.GetCompEM())
			bat = b.GetCompEM().GetEnergy().ToString() + "/" + b.GetCompEM().GetEnergyMax().ToString();
		Print("[Drezina] motor: запуск ok=" + ok + " state=" + state + " (1 сломан, 2 нет бензина, 4 нет свечи, 8 нет аккумулятора) бензин=" + GetFluidFraction(CarFluid.FUEL) + " аккумулятор=" + bat + " свеча=" + FindAttachmentBySlotName("SparkPlug"));
		return ok;
	}

	// ------------------------------------------------------------------ путь

	DrezinaTrack GetTrack()
	{
		if (m_TrackId < 0)
			return null;
		return DrezinaTrackManager.Get().GetTrack(m_TrackId);
	}

	// сервер: поставить на путь (при выдаче со станции)
	void ServerPlaceOnTrack(int trackId, float dist, int face)
	{
		m_TrackId = trackId;
		m_Face = face;
		m_DistHint = dist;
		DrezinaTrack t = GetTrack();
		if (t)
		{
			vector mat[4];
			TrackTransform(t, dist, mat);
			SetTransform(mat);
		}
		SetSynchDirty();
		Print("[Drezina] motor: на пути #" + trackId + ", дистанция " + dist + ", нос " + face);
	}

	// дистанция по пути, ближайшая к точке (проекция с уточнением от прошлой дистанции)
	float ProjectDist(DrezinaTrack t, vector pos)
	{
		float d = m_DistHint;
		if (d < 0)
		{
			float off;
			d = t.ClosestDistance(pos, off);
		}
		for (int i = 0; i < 3; i++)
		{
			vector p, dir;
			t.GetPosDir(d, p, dir);
			d = Math.Clamp(d + vector.Dot(pos - p, dir), 0, t.GetLength());
		}
		return d;
	}

	void TrackTransform(DrezinaTrack t, float d, out vector mat[4])
	{
		vector p, dir;
		t.GetPosDir(d, p, dir);
		float faceSign = m_Face;
		vector fwd = dir * faceSign;
		vector right = (vector.Up * fwd).Normalized();
		vector up = fwd * right;
		p[1] = p[1] + DrezinaSettings.Get().RailHeightOffset + HOVER;
		mat[0] = right;
		mat[1] = up;
		mat[2] = fwd;
		mat[3] = p;
	}

	// После каждого шага физики (сервер и машина водителя на его клиенте): машина — на рельсы,
	// скорость — только вдоль пути. Состояние не храним: всё берём из положения и скорости тела,
	// поэтому сетевые поправки сервера не дёргают машину.
	override void EOnPostSimulate(IEntity other, float timeSlice)
	{
		super.EOnPostSimulate(other, timeSlice);
		RailStep(timeSlice);
	}

	void RailStep(float dt)
	{
		if (dt <= 0)
			return;
		bool server = GetGame().IsServer();
		if (!server && !IsOwner())
			return;
		if (m_OffRail)
			return;          // снята с рельсов: стоит, где поставили (физика спит)

		if (m_TrackId < 0 && server)
		{
			// после перезапуска или выставленная вручную — ищем путь рядом
			int found = DrezinaTrackManager.Get().FindNearestTrack(GetPosition(), 4.0);
			if (found > 0)
			{
				m_TrackId = found;
				SetSynchDirty();
				Print("[Drezina] motor: найден путь #" + found);
			}
		}
		DrezinaTrack t = GetTrack();
		if (!t)
			return;

		if (!m_GravityOff)
		{
			m_GravityOff = true;
			dBodyEnableGravity(this, false);
		}

		float d = ProjectDist(t, GetPosition());
		vector p, dir;
		t.GetPosDir(d, p, dir);
		float faceSign = m_Face;
		vector fwd = dir * faceSign;
		float v = vector.Dot(GetVelocity(this), fwd);

		// управление: газ работает только с заведённым мотором и включённой передачей
		float throttle = 0;
		float brake = 0;
		float handbrake = 0;
		int gear = GetGear();
		if (CrewDriver())
		{
			brake = GetBrake();
			handbrake = GetHandbrake();
			if (EngineIsOn())
				throttle = GetThrottle();
		}
		else
		{
			handbrake = 1;   // без водителя стоит на ручнике
		}

		float maxV = 0;
		float sign = 1;
		// передачи: R — назад до 11 км/ч, N, D (единственная передача вперёд) — до 50 км/ч
		if (gear == CarGear.REVERSE)
		{
			maxV = 3.0;
			sign = -1;
		}
		else if (gear == CarGear.NEUTRAL)
		{
			maxV = 0;
		}
		else
		{
			maxV = MAX_SPEED;
		}

		// разгон в сторону передачи до предела передачи
		if (throttle > 0.01 && maxV > 0)
		{
			float target = maxV * sign;
			if ((sign > 0 && v < target) || (sign < 0 && v > target))
				v = v + sign * ACCEL * throttle * dt;
		}
		// торможение и накат к нулю
		float decel = ROLL_DECEL + brake * BRAKE_DECEL + handbrake * HANDBRAKE_DECEL;
		if (throttle <= 0.01 || maxV == 0)
		{
			float dv = decel * dt;
			if (Math.AbsFloat(v) <= dv)
				v = 0;
			else
				v = v - dv * Math.Sign(v);
		}

		// другие дрезины на пути впереди
		if (v != 0 && IsBlocked(t, d, v))
			v = 0;

		float nd = d + v * m_Face * dt;
		// стрелки и примыкания развязок метро: переход на другой путь
		if (v != 0 && TryTransfer(t, d, nd, v))
		{
			t = GetTrack();
			nd = m_DistHint;
		}
		// страховка: серверная копия разошлась с водителем больше чем на 25 м (что-то пошло не так) —
		// ставим туда, где дрезина у водителя. Мелкие расхождения правит сама игра (откат машины).
		if (server && m_CliTime > 0 && m_CliTrack == t.GetId() && RemoteDriver() && GetGame().GetTime() - m_CliTime < 500)
		{
			float pred = m_CliD + m_CliV * m_Face * (GetGame().GetTime() - m_CliTime) / 1000.0;
			if (Math.AbsFloat(pred - nd) > 25.0)
				nd = pred;
		}
		// у торцов пути останавливаемся за 1.6 м (там тупиковый упор станции); у примыканий — едем дальше
		float lo = Math.Min(END_GAP, t.GetLength() * 0.5);
		float hi = Math.Max(t.GetLength() - END_GAP, lo);
		// у конца со стрелкой съездов (линия, подключённая к другой) — тоже до самого конца
		bool linked0 = t.LinkAt(0) != null || t.SwitchNearEnd(0);
		bool linked1 = t.LinkAt(1) != null || t.SwitchNearEnd(1);
		if (HasTrailer())
		{
			// прицеп сзади (на стороне -нос): ему тоже нужно место до торца
			if (m_Face > 0 && !linked0)
				lo = Math.Min(lo + TRAILER_GAP, hi);
			else if (m_Face < 0 && !linked1)
				hi = Math.Max(hi - TRAILER_GAP, lo);
		}
		if (linked0)
			lo = 0;
		if (linked1)
			hi = t.GetLength();
		if (nd <= lo || nd >= hi)
		{
			nd = Math.Clamp(nd, lo, hi);
			if (!linked0 && !linked1)
				v = 0;
			else if ((nd <= lo && !linked0) || (nd >= hi && !linked1))
				v = 0;
		}
		m_DistHint = nd;

		vector mat[4];
		TrackTransform(t, nd, mat);
		SetTransform(mat);
		SetVelocity(this, mat[2] * v);

		// водитель сообщает серверу, где дрезина: серверная копия не уходит вперёд/назад
		if (!server)
		{
			m_PosSendTimer -= dt;
			if (m_PosSendTimer <= 0 && (v != 0 || m_PosSendTimer < -2))
			{
				m_PosSendTimer = 0.5;
				ScriptRPC prpc = new ScriptRPC();
				prpc.Write(m_TrackId);
				prpc.Write(nd);
				prpc.Write(v);
				prpc.Send(this, DrezinaRPC.MOTOR_POS, false, null);
			}
		}

		// стоим и газа нет — усыпляем физику: тело больше не шевелится (иначе дрожь на месте)
		if (v == 0 && throttle <= 0.01)
		{
			m_StillTime += dt;
			if (m_StillTime > 0.3 && !m_Sleeping && !CrewDriver())   // с водителем не усыпляем: просыпание по кадру у сервера и клиента в разный момент — расхождение
			{
				m_Sleeping = true;
				dBodyActive(this, ActiveState.INACTIVE);
			}
		}
		else
		{
			m_StillTime = 0;
		}

		m_LogTimer -= dt;
		if (m_LogTimer <= 0 && CrewDriver())
		{
			m_LogTimer = 2.0;
			Print("[Drezina] motor server=" + server + " d=" + nd + " v=" + v + " gear=" + gear + " thr=" + throttle + " engine=" + EngineIsOn());
		}
	}

	bool IsBlocked(DrezinaTrack t, float d, float v)
	{
		float clearance = DrezinaSettings.Get().HandcarClearance;
		// головная точка по ходу: при езде задом с прицепом — прицеп
		float moveDir = m_Face * Math.Sign(v);
		float head = d;
		if (HasTrailer() && moveDir == -m_Face)
			head = d - m_Face * TRAILER_GAP;
		foreach (Drezina_Motor o : s_All)
		{
			if (!o || o == this || o.m_TrackId != m_TrackId || o.m_OffRail)
				continue;          // снятая с рельсов не мешает: так и разъезжаются
			float od = ProjectDistOf(t, o.GetPosition());
			float ahead = (od - head) * moveDir;
			if (ahead > 0 && ahead < clearance)
				return true;
		}
		// прицепы других мотодрезин: их хвост на TRAILER_GAP позади
		foreach (Drezina_Motor ot : s_All)
		{
			if (!ot || ot == this || !ot.HasTrailer() || ot.m_TrackId != m_TrackId || ot.m_OffRail)
				continue;
			float otd = ProjectDistOf(t, ot.GetPosition()) - ot.m_Face * TRAILER_GAP;
			float aheadT = (otd - head) * moveDir;
			if (aheadT > 0 && aheadT < clearance)
				return true;
		}
		return false;
	}

	// ------------------------------------------------------------------ стрелки

	// Пересекли стрелку, едучи в её сторону, с рулём к ветке — уходим на ветку; доехали до конца
	// служебного пути — переходим на путь, к которому он примыкает. Руль: A/D (вправо — плюс).
	bool TryTransfer(DrezinaTrack t, float d, float nd, float v)
	{
		int md = 1;
		if (nd < d)
			md = -1;
		DrezinaTrackManager tm = DrezinaTrackManager.Get();
		float steer = 0;
		if (CrewDriver())
			steer = GetSteering();
		m_SinceTransfer += Math.AbsFloat(nd - d);
		foreach (DrezinaSwitch sw : t.m_Switches)
		{
			if (sw.Dir != md)
				continue;
			if (m_SinceTransfer < 7.0)
				continue;                       // сразу после стрелки следующую не берём (на кольце съезды рядом)
			if ((sw.D - d) * md <= 0 || (nd - sw.D) * md < 0)
				continue;                       // эту стрелку в этом шаге не пересекли
			if (sw.Side != 2 && steer * sw.Side < 0.35)
			{
				// у конца линии с двумя съездами руль не тронут — уходим направо, а не в упор
				float swEnd = 0;
				if (sw.Dir > 0)
					swEnd = t.GetLength();
				bool atEnd = Math.AbsFloat(sw.D - swEnd) < 1.0;
				if (!(atEnd && sw.Side == 1 && Math.AbsFloat(steer) < 0.35))
					continue;
			}                       // руль не в сторону ветки — едем прямо
			DrezinaTrack b = tm.GetTrack(sw.Branch);
			if (!b)
				continue;
			float over = Math.AbsFloat(nd - sw.D);
			float entry = 0;
			int bmd = 1;
			if (sw.BranchEnd == 1)
			{
				entry = b.GetLength();
				bmd = -1;
			}
			DoTransfer(sw.D, md, sw.Branch, entry, entry + bmd * over, bmd, v);
			return true;
		}
		int end = -1;
		float over2 = 0;
		if (nd < 0)
		{
			end = 0;
			over2 = -nd;
		}
		else if (nd > t.GetLength())
		{
			end = 1;
			over2 = nd - t.GetLength();
		}
		if (end < 0)
			return false;
		DrezinaLink l = t.LinkAt(end);
		if (!l || !tm.GetTrack(l.ToTrack))
			return false;
		float fromD = 0;
		if (end == 1)
			fromD = t.GetLength();
		DoTransfer(fromD, md, l.ToTrack, l.ToD, l.ToD + l.MergeDir * over2, l.MergeDir, v);
		return true;
	}

	void DoTransfer(float fromD, int fromMove, int toId, float entryD, float toD, int toMove, float v)
	{
		m_PrevTrack = m_TrackId;
		m_PrevD = fromD;
		m_PrevMove = fromMove;
		m_PrevFace = m_Face;
		m_EntryD = entryD;
		m_TrackId = toId;
		if (v >= 0)
			m_Face = toMove;
		else
			m_Face = -toMove;
		m_DistHint = toD;
		m_TransferTime = GetGame().GetTime();
		m_SinceTransfer = 0;
		if (GetGame().IsServer())
		{
			SetSynchDirty();
		}
		else
		{
			m_SyncedTrack = m_TrackId;
			m_LTrack = m_TrackId;
			m_LFace = m_Face;
			m_LPrevTrack = m_PrevTrack;
			m_LPrevD = m_PrevD;
			m_LPrevMove = m_PrevMove;
			m_LPrevFace = m_PrevFace;
			m_LEntryD = m_EntryD;
			ScriptRPC rpc = new ScriptRPC();
			rpc.Write(m_TrackId);
			rpc.Write(toD);
			rpc.Write(m_Face);
			rpc.Write(m_PrevTrack);
			rpc.Write(m_PrevD);
			rpc.Write(m_PrevMove);
			rpc.Write(m_PrevFace);
			rpc.Write(m_EntryD);
			// при повторной прокрутке ввода после отката тот же переход не шлём ещё раз
			if (toId != m_SentTransferTrack || GetGame().GetTime() - m_SentTransferTime > 1500)
			{
				m_SentTransferTrack = toId;
				m_SentTransferTime = GetGame().GetTime();
				rpc.Send(this, DrezinaRPC.MOTOR_TRANSFER, true, null);
			}
		}
		Print("[Drezina] motor: стрелка, путь #" + m_PrevTrack + " -> #" + m_TrackId);
	}

	int m_SyncedTrack = -1;
	float m_PosSendTimer = 0;
	// последнее положение от водителя (сервер плавно подтягивает к нему свою копию)
	int m_CliTrack = -1;
	float m_CliD;
	float m_CliV;
	int m_CliTime = 0;
	int m_SentTransferTrack = -1;
	int m_SentTransferTime = 0;
	Drezina_LanternLight m_Lantern;

	protected override event typename GetOwnerStateType()
	{
		return Drezina_MotorOwnerState;
	}

	protected override event void ObtainState(/*inout*/ PawnOwnerState pState)
	{
		super.ObtainState(pState);
		Drezina_MotorOwnerState st = Drezina_MotorOwnerState.Cast(pState);
		if (!st)
			return;
		st.m_dTrack = m_TrackId;
		st.m_dFace = m_Face;
		st.m_dPrevTrack = m_PrevTrack;
		st.m_dPrevD = m_PrevD;
		st.m_dPrevMove = m_PrevMove;
		st.m_dPrevFace = m_PrevFace;
		st.m_dEntryD = m_EntryD;
		st.m_dSince = m_SinceTransfer;
		st.m_dHint = m_DistHint;
	}

	protected override event void RewindState(PawnOwnerState pState, /*inout*/ PawnMove pMove, inout NetworkRewindType pRewindType)
	{
		super.RewindState(pState, pMove, pRewindType);
		Drezina_MotorOwnerState st = Drezina_MotorOwnerState.Cast(pState);
		if (!st || st.m_dTrack < 0.5)
			return;
		m_TrackId = Math.Round(st.m_dTrack);
		m_Face = Math.Round(st.m_dFace);
		m_PrevTrack = Math.Round(st.m_dPrevTrack);
		m_PrevD = st.m_dPrevD;
		m_PrevMove = Math.Round(st.m_dPrevMove);
		m_PrevFace = Math.Round(st.m_dPrevFace);
		m_EntryD = st.m_dEntryD;
		m_SinceTransfer = st.m_dSince;
		m_DistHint = st.m_dHint;
		// локальные копии клиента — тоже к состоянию сервера (их сверяет OnVariablesSynchronized)
		m_LTrack = m_TrackId;
		m_LFace = m_Face;
		m_LPrevTrack = m_PrevTrack;
		m_LPrevD = m_PrevD;
		m_LPrevMove = m_PrevMove;
		m_LPrevFace = m_PrevFace;
		m_LEntryD = m_EntryD;
		m_SyncedTrack = m_TrackId;
	}

	// водитель — игрок (на сервере у него всегда есть identity)
	Human RemoteDriver()
	{
		Human h = CrewDriver();
		if (h && h.GetIdentity())
			return h;
		return null;
	}

	bool IsSenderDriver(PlayerIdentity sender)
	{
		Human h = RemoteDriver();
		return sender && h && h.GetIdentity().GetId() == sender.GetId();
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);
		if (!GetGame().IsServer())
			return;
		if (rpc_type == DrezinaRPC.MOTOR_TRANSFER)
		{
			int toId, face, prevTrack, prevMove, prevFace;
			float toD, prevD, entryD;
			if (!ctx.Read(toId) || !ctx.Read(toD) || !ctx.Read(face) || !ctx.Read(prevTrack) || !ctx.Read(prevD) || !ctx.Read(prevMove) || !ctx.Read(prevFace) || !ctx.Read(entryD))
				return;
			if (!IsSenderDriver(sender) || m_OffRail || m_TrackId == toId)
				return;                                // сервер уже перешёл сам
			DrezinaTrack nt = DrezinaTrackManager.Get().GetTrack(toId);
			if (!nt)
				return;
			m_PrevTrack = prevTrack;
			m_PrevD = prevD;
			m_PrevMove = prevMove;
			m_PrevFace = prevFace;
			m_EntryD = entryD;
			m_TrackId = toId;
			m_Face = face;
			m_TransferTime = GetGame().GetTime();
			m_SinceTransfer = 0;
			m_CliTrack = toId;
			m_CliD = toD;
			m_CliTime = GetGame().GetTime();
			ServerSnapTo(nt, toD);
			SetSynchDirty();
			Print("[Drezina] motor: стрелка (от водителя), путь #" + prevTrack + " -> #" + toId);
			return;
		}
		if (rpc_type == DrezinaRPC.MOTOR_POS)
		{
			int pid;
			float pd, pv;
			if (!ctx.Read(pid) || !ctx.Read(pd) || !ctx.Read(pv))
				return;
			if (!IsSenderDriver(sender) || m_OffRail || pid != m_TrackId)
				return;
			m_CliTrack = pid;
			m_CliD = pd;
			m_CliV = pv;
			m_CliTime = GetGame().GetTime();
			if (m_Sleeping)
				Wake();
		}
	}

	// серверная копия — на дистанцию d пути t (по данным водителя)
	void ServerSnapTo(DrezinaTrack t, float d)
	{
		m_DistHint = d;
		vector mat[4];
		TrackTransform(t, d, mat);
		SetTransform(mat);
		Wake();
	}

	// керосиновый фонарь на штанге (правый передний угол): горит всегда, тускло — видно на пару корпусов вокруг
	void LanternTick(float dt)
	{
		if (m_Lantern)
			return;
		m_Lantern = Drezina_LanternLight.Cast(ScriptedLightBase.CreateLight(Drezina_LanternLight, GetPosition()));
		if (m_Lantern)
			m_Lantern.AttachOnObject(this, Vector(0.64, 1.5, 1.26), vector.Zero);
	}

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();
		if (GetGame().IsServer())
			return;
		// водитель только что сам перешёл на стрелке, а сервер ещё не прислал этот переход
		if (IsOwner() && GetGame().GetTime() - m_TransferTime < 3000 && m_TrackId != m_LTrack)
		{
			m_TrackId = m_LTrack;
			m_Face = m_LFace;
			m_PrevTrack = m_LPrevTrack;
			m_PrevD = m_LPrevD;
			m_PrevMove = m_LPrevMove;
			m_PrevFace = m_LPrevFace;
			m_EntryD = m_LEntryD;
		}
		// путь сменился с сервера: старая дистанция относится к другому пути — ищем заново
		// (иначе машину бросало по чужой дистанции — «телепорты» на стрелках)
		if (m_TrackId != m_SyncedTrack)
		{
			if (m_TrackId != m_LTrack || GetGame().GetTime() - m_TransferTime >= 3000)
				m_DistHint = -1;
			m_SyncedTrack = m_TrackId;
			m_LTrack = m_TrackId;
		}
	}

	// Где прицеп: на TRAILER_GAP позади по текущему пути, а сразу после стрелки — ещё на прежнем.
	void TrailerPose(DrezinaTrack t, float d, out DrezinaTrack tt, out float td, out int tface)
	{
		tt = t;
		tface = m_Face;
		td = d - m_Face * TRAILER_GAP;
		if (m_PrevTrack <= 0 || Math.AbsFloat(d - m_EntryD) > TRAILER_GAP)
			return;
		if ((td - m_EntryD) * (d - m_EntryD) >= 0)
			return;                            // прицеп уже прошёл точку перехода
		DrezinaTrack pt = DrezinaTrackManager.Get().GetTrack(m_PrevTrack);
		if (!pt)
			return;
		float over = Math.AbsFloat(td - m_EntryD);
		tt = pt;
		td = m_PrevD - m_PrevMove * over;
		tface = m_PrevFace;
	}

	// ------------------------------------------------------------------ прицеп

	bool HasTrailer()
	{
		return m_TrailerType != 0;
	}

	// прицепить у терминала: прицеп «встаёт» сзади; если сзади мало места — мотодрезина откатывается вперёд
	bool ServerAttachTrailer(int type)
	{
		DrezinaTrack t = GetTrack();
		if (!t || m_OffRail || HasTrailer() || type < 1 || type > 2)
			return false;
		float len = t.GetLength();
		float d = ProjectDist(t, GetPosition());
		float lo = END_GAP;
		float hi = len - END_GAP;
		if (m_Face > 0)
			lo += TRAILER_GAP;
		else
			hi -= TRAILER_GAP;
		if (lo > hi)
			return false;
		d = Math.Clamp(d, lo, hi);
		m_DistHint = d;
		vector mat[4];
		TrackTransform(t, d, mat);
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		Wake();
		m_TrailerType = type;
		if (type == 2)
		{
			for (int i = 0; i < 4; i++)
				GetInventory().CreateAttachment("Drezina_TrailerBarrel");
		}
		SetSynchDirty();
		Print("[Drezina] прицеплен прицеп, тип " + type);
		return true;
	}

	// отцепить: бочки (пустые) убираем
	void ServerDetachTrailer()
	{
		array<EntityAI> barrels = new array<EntityAI>;
		for (int i = 0; i < GetInventory().AttachmentCount(); i++)
		{
			Drezina_TrailerBarrel b = Drezina_TrailerBarrel.Cast(GetInventory().GetAttachmentFromIndex(i));
			if (b)
				barrels.Insert(b);
		}
		foreach (EntityAI e : barrels)
			GetGame().ObjectDelete(e);
		m_TrailerType = 0;
		SetSynchDirty();
	}

	// в прицепе кто-то сидит (места 3..6)
	bool TrailerSeatsTaken()
	{
		for (int i = 3; i < CrewSize(); i++)
		{
			if (CrewMember(i))
				return true;
		}
		return false;
	}

	// все бочки пустые
	bool BarrelsEmpty()
	{
		for (int i = 0; i < GetInventory().AttachmentCount(); i++)
		{
			Drezina_TrailerBarrel b = Drezina_TrailerBarrel.Cast(GetInventory().GetAttachmentFromIndex(i));
			if (b && b.GetInventory().GetCargo() && b.GetInventory().GetCargo().GetItemCount() > 0)
				return false;
		}
		return true;
	}

	// ------------------------------------------------------------------ видимый прицеп (клиент)
	// Прицеп — только картинка: каждый клиент держит у себя локальную модель и ставит её за дрезиной
	// после каждого кадра (по положению дрезины, которое он сам видит). По сети отдельно не ходит —
	// значит, не дребезжит и не отстаёт; на поворотах и кольцах встаёт по пути (изгибается со стрелкой).
	Object m_TrVis;
	int m_TrVisType;
	float m_TrWheel;
	bool m_TrBrake;
	Drezina_TailLight m_TrTail;
	float m_TrHint = -1;
	int m_TrHintTrack;
	int m_TrLastTime;

	void UpdateTrailerVis()
	{
		if (GetGame().IsDedicatedServer())
			return;
		if (m_TrVisType != m_TrailerType)
			DestroyTrailerVis();
		if (m_TrailerType == 0)
			return;
		if (!m_TrVis)
		{
			string cls = "Drezina_TrailerVisPassenger";
			if (m_TrailerType == 2)
				cls = "Drezina_TrailerVisCargo";
			m_TrVis = GetGame().CreateObjectEx(cls, GetPosition(), ECE_LOCAL);
			m_TrVisType = m_TrailerType;
			m_TrBrake = false;
			if (!m_TrVis)
				return;
		}
		vector mat[4];
		DrezinaTrack t = GetTrack();
		if (!m_OffRail && t)
		{
			float ld = m_TrHint;
			if (m_TrHintTrack != t.GetId())
				ld = -1;
			m_TrHintTrack = t.GetId();
			vector lp = GetPosition();
			if (ld < 0)
			{
				float off;
				ld = t.ClosestDistance(lp, off);
			}
			for (int i = 0; i < 3; i++)
			{
				vector pp, pdir;
				t.GetPosDir(ld, pp, pdir);
				ld = Math.Clamp(ld + vector.Dot(lp - pp, pdir), 0, t.GetLength());
			}
			m_TrHint = ld;
			DrezinaTrack tt;
			float td;
			int tface;
			TrailerPose(t, ld, tt, td, tface);
			TrackTransformFace(tt, Math.Clamp(td, 0, tt.GetLength()), tface, mat);
		}
		else
		{
			// снята с рельсов — прицеп ровно сзади
			GetTransform(mat);
			mat[3] = mat[3] - mat[2] * TRAILER_GAP;
		}
		m_TrVis.SetTransform(mat);

		// колёса
		int now = GetGame().GetTime();
		float dt = (now - m_TrLastTime) / 1000.0;
		m_TrLastTime = now;
		if (dt > 0 && dt < 0.5)
		{
			float speed = vector.Dot(GetVelocity(this), GetDirection());
			m_TrWheel += speed * dt / (Math.PI2 * WHEEL_RADIUS);
			m_TrWheel -= Math.Floor(m_TrWheel);
			m_TrVis.SetAnimationPhase("drezina_wheels", m_TrWheel);
		}

		// стоп-сигнал прицепа
		bool lit = BrakeLit() && !m_OffRail;
		if (lit != m_TrBrake)
		{
			m_TrBrake = lit;
			if (lit)
			{
				m_TrVis.SetObjectMaterial(2, "Drezina\\data\\textures\\drezina_redglass_e.rvmat");
				if (!m_TrTail)
				{
					m_TrTail = Drezina_TailLight.Cast(ScriptedLightBase.CreateLight(Drezina_TailLight, m_TrVis.GetPosition()));
					if (m_TrTail)
						m_TrTail.AttachOnObject(m_TrVis, m_TrVis.GetMemoryPointPos("light_reverse") + Vector(0, 0, -0.15), vector.Zero);
				}
			}
			else
			{
				m_TrVis.SetObjectMaterial(2, "Drezina\\data\\textures\\drezina_redglass.rvmat");
				if (m_TrTail)
				{
					m_TrTail.Destroy();
					m_TrTail = null;
				}
			}
		}
	}

	void DestroyTrailerVis()
	{
		if (m_TrTail)
		{
			m_TrTail.Destroy();
			m_TrTail = null;
		}
		if (m_TrVis && GetGame())
			GetGame().ObjectDelete(m_TrVis);
		m_TrVis = null;
		m_TrVisType = 0;
	}

	override void EOnPostFrame(IEntity other, int extra)
	{
		super.EOnPostFrame(other, extra);
		UpdateTrailerVis();
	}

	// поставить машину с ориентацией face (общая формула и для прицепа)
	static void TrackTransformFace(DrezinaTrack t, float d, int face, out vector mat[4])
	{
		vector p, dir;
		t.GetPosDir(d, p, dir);
		float faceSign = face;
		vector fwd = dir * faceSign;
		vector right = (vector.Up * fwd).Normalized();
		vector up = fwd * right;
		p[1] = p[1] + DrezinaSettings.Get().RailHeightOffset + HOVER;
		mat[0] = right;
		mat[1] = up;
		mat[2] = fwd;
		mat[3] = p;
	}

	static float ProjectDistOf(DrezinaTrack t, vector pos)
	{
		float off;
		return t.ClosestDistance(pos, off);
	}

	// ------------------------------------------------------------------ вращение колёс (клиенты)

	override void EOnPostFrame(IEntity other, int extra)
	{
		super.EOnPostFrame(other, extra);
		if (GetGame().IsDedicatedServer())
			return;
		int now = GetGame().GetTime();
		float dt = (now - m_LastFrameTime) * 0.001;
		m_LastFrameTime = now;
		if (dt <= 0 || dt > 0.5)
			return;
		vector vel = GetVelocity(this);
		float speed = vector.Dot(vel, GetDirection());
		m_WheelPhase += speed * dt / (Math.PI2 * WHEEL_RADIUS);
		m_WheelPhase -= Math.Floor(m_WheelPhase);
		SetAnimationPhase("drezina_wheels", m_WheelPhase);
	}

	// ------------------------------------------------------------------ сдача на станции

	// ------------------------------------------------------------------ разворот, снять / поставить на рельсы

	// стоит, пустая, на пути
	bool CanManhandle()
	{
		return CanBeReturned() && !EngineIsOn();
	}

	bool CanTurnAround()
	{
		return CanManhandle() && !m_OffRail && GetTrack() != null;
	}

	bool CanTakeOffRail()
	{
		return CanManhandle() && !m_OffRail && GetTrack() != null;
	}

	bool CanPutOnRail()
	{
		return CanManhandle() && m_OffRail;
	}

	bool ServerTurnAround()
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return false;
		float d = ProjectDist(t, GetPosition());
		if (HasTrailer())
		{
			// прицеп переходит на другую сторону (снова сзади); места должно хватить до торца
			float td = d + m_Face * TRAILER_GAP;
			if (td < END_GAP || td > t.GetLength() - END_GAP)
				return false;
		}
		m_Face = -m_Face;
		m_DistHint = d;
		vector mat[4];
		TrackTransform(t, d, mat);
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		Wake();
		SetSynchDirty();
		Print("[Drezina] motor: развёрнута, нос " + m_Face);
		return true;
	}

	// сдвинуть вбок от пути на свободную сторону (куда луч не упирается в стену) и поставить на землю
	bool ServerTakeOffRail()
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return false;
		float d = ProjectDist(t, GetPosition());
		vector mat[4];
		TrackTransform(t, d, mat);
		vector center = mat[3] + Vector(0, 0.8, 0);
		vector hitPos, hitDir;
		int hitComp;
		float off = 2.1;
		vector place = vector.Zero;
		float sgn = 1;
		// сначала пробуем дальше от пути, потом ближе (в тоннеле до стены всего 3 м); встречной дрезине
		// хватает 1.7 м от оси
		float offs[3] = {2.1, 1.9, 1.7};
		for (int oi = 0; oi < 3 && place == vector.Zero; oi++)
		{
			off = offs[oi];
			for (int k = 0; k < 2; k++)
			{
				sgn = 1;
				if (k == 1)
					sgn = -1;
				vector side = mat[0] * sgn;
				// луч до дальнего борта дрезины в стоящем положении (+0.85 м); с прицепом — и у прицепа
				if (DayZPhysics.RaycastRV(center, center + side * (off + 0.85), hitPos, hitDir, hitComp, null, null, this, false, false, ObjIntersectGeom))
					continue;
				if (HasTrailer())
				{
					// место сбоку и у прицепа (он в TRAILER_GAP позади)
					vector tc = center - mat[2] * TRAILER_GAP;
					if (DayZPhysics.RaycastRV(tc, tc + side * (off + 0.85), hitPos, hitDir, hitComp, null, null, this, false, false, ObjIntersectGeom))
						continue;
				}
				place = mat[3] + side * off;
				break;
			}
		}
		if (place == vector.Zero)
			return false;
		// земля под новым местом
		vector top = place + Vector(0, 1.5, 0);
		if (DayZPhysics.RaycastRV(top, place - Vector(0, 3.0, 0), hitPos, hitDir, hitComp, null, null, this))
			place[1] = hitPos[1] + 0.05;
		mat[3] = place;
		m_OffRail = true;
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		// физика включена и с гравитацией: машина садится на пол и её новое место уходит всем клиентам
		// (раньше тело сразу усыплялось — положение не обновлялось, дрезина оставалась на рельсах)
		dBodyEnableGravity(this, true);
		m_GravityOff = false;
		Wake();
		SetSynchDirty();
		Print("[Drezina] motor: снята с рельсов");
		return true;
	}

	// разбудить физику: RailStep снова ставит машину на путь, а новое положение уходит клиентам
	void Wake()
	{
		m_Sleeping = false;
		m_StillTime = 0;
		dBodyActive(this, ActiveState.ACTIVE);
	}

	bool ServerPutOnRail()
	{
		int found = DrezinaTrackManager.Get().FindNearestTrack(GetPosition(), 4.0);
		if (found <= 0)
			return false;
		m_TrackId = found;
		DrezinaTrack t = GetTrack();
		if (!t)
			return false;
		float off;
		float d = t.ClosestDistance(GetPosition(), off);
		d = Math.Clamp(d, END_GAP, Math.Max(t.GetLength() - END_GAP, END_GAP));
		// нос туда, куда он смотрел
		vector p, dir;
		t.GetPosDir(d, p, dir);
		if (vector.Dot(GetDirection(), dir) >= 0)
			m_Face = 1;
		else
			m_Face = -1;
		// с прицепом: место сзади до торца
		if (HasTrailer())
		{
			if (m_Face > 0)
				d = Math.Max(d, END_GAP + TRAILER_GAP);
			else
				d = Math.Min(d, t.GetLength() - END_GAP - TRAILER_GAP);
		}
		m_OffRail = false;
		m_DistHint = d;
		vector mat[4];
		TrackTransform(t, d, mat);
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		Wake();
		SetSynchDirty();
		Print("[Drezina] motor: поставлена на путь #" + found);
		return true;
	}

	bool CanBeReturned()
	{
		if (CrewSize() > 0)
		{
			for (int i = 0; i < CrewSize(); i++)
			{
				if (CrewMember(i))
					return false;
			}
		}
		if (GetVelocity(this).Length() > 0.5)
			return false;
		return true;
	}

	bool CargoEmpty()
	{
		if (!BarrelsEmpty())
			return false;
		if (!GetInventory() || !GetInventory().GetCargo())
			return true;
		return GetInventory().GetCargo().GetItemCount() == 0;
	}

	// тормоз нажат (синхронизируется ванильной машиной) — для стоп-сигнала прицепа
	bool BrakeLit()
	{
		return m_BrakesArePressed;
	}

}

// Фара мотодрезины: профиль ванильного мотоцикла, но в 3 раза тусклее
class Drezina_MotorLightProfileFront : Motorbike_01LightProfileFront
{
	void Drezina_MotorLightProfileFront()
	{
		// фары разбиты: даже «включённые» не светят
		m_SegregatedBrightness 	= 0;
		m_AggregatedBrightness 	= 0;
		m_SegregatedRadius 		= 0.1;
		m_AggregatedRadius 		= 0.1;
		m_FlaresVisible 		= false;
	}
}

// Свет фонаря «летучая мышь»: тёплый, тусклый, без тени
class Drezina_LanternLight extends PointLightBase
{
	void Drezina_LanternLight()
	{
		SetVisibleDuringDaylight(false);
		SetRadiusTo(6.5);
		SetBrightnessTo(1.1);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(1.0, 0.68, 0.36);
		SetAmbientColor(1.0, 0.68, 0.36);
	}
}
