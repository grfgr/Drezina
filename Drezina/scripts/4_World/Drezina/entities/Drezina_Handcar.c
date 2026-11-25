// Дрезина. Движется по пути скриптом (без физики машины):
//  - сервер считает дистанцию по пути и скорость, синхронизирует их;
//  - каждый клиент сам строит ту же геометрию пути и плавно ставит дрезину на нужную дистанцию;
//  - водитель стоит на платформе через DrezinaRideCommand (HumanCommandScript).

class Drezina_Handcar extends ItemBase
{
	static const float DECK_HEIGHT   = 0.62;  // высота пола платформы от головки рельса
	static const float SEAT_BACK     = 0.80;  // насколько водитель стоит за рычагом (по ходу)
	static const float WHEEL_RADIUS  = 0.36;

	// --- синхронизируемое состояние
	int   m_TrackId;
	float m_SyncDist;
	float m_SyncSpeed;
	int   m_Dir = 1;        // 1 — по росту дистанции, -1 — обратно
	bool  m_Pumping;
	int   m_DriverLow;
	int   m_DriverHigh;

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

	void Drezina_Handcar()
	{
		RegisterNetSyncVariableInt("m_TrackId");
		RegisterNetSyncVariableFloat("m_SyncDist", 0, 200000, 2);
		RegisterNetSyncVariableFloat("m_SyncSpeed", 0, 100, 2);
		RegisterNetSyncVariableInt("m_Dir", -1, 1);
		RegisterNetSyncVariableBool("m_Pumping");
		RegisterNetSyncVariableInt("m_DriverLow");
		RegisterNetSyncVariableInt("m_DriverHigh");

		SetEventMask(EntityEvent.FRAME);
		DrezinaTrackManager.Get().RegisterHandcar(this);
	}

	void ~Drezina_Handcar()
	{
		if (DrezinaTrackManager.s_Instance)
			DrezinaTrackManager.s_Instance.UnregisterHandcar(this);
	}

	override void EEDelete(EntityAI parent)
	{
		super.EEDelete(parent);
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
		SetSynchDirty();
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
			if (ctx.Read(p) && IsSenderDriver(sender))
				m_Throttle = Math.Clamp(p.param1, -1, 1);
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
				ServerClearDriver();
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
			if (!m_Driver || !m_Driver.IsAlive() || m_Driver.IsUnconscious() || !m_Driver.GetIdentity() || vector.Distance(m_Driver.GetPosition(), GetPosition()) > 6.0)
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

		vector pos, dir;
		t.GetPosDir(m_Dist, pos, dir);

		float accel = -st.RollingFriction;
		if (m_Throttle > 0)
			accel += st.PumpAcceleration;
		else if (m_Throttle < 0)
			accel -= st.BrakeDeceleration;
		// уклон: dir[1] — вертикальная составляющая направления пути
		accel -= st.SlopeFactor * dir[1] * m_Dir;

		m_Speed = Math.Clamp(m_Speed + accel * dt, 0, st.MaxSpeed);

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
		ApplyTransform();

		// синхронизация ~10 раз в секунду или при смене состояния
		m_SyncTimer += dt;
		if (m_SyncTimer >= 0.1 || pumping != m_Pumping)
		{
			m_SyncTimer = 0;
			m_Pumping = pumping;
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
		if (Math.AbsFloat(m_SyncDist - m_Dist) > 3.0)
			m_Dist = m_SyncDist;
		m_Speed = m_SyncSpeed;
	}

	void ClientSimulate(float dt)
	{
		DrezinaTrack t = GetTrack();
		if (!t)
			return; // геометрии ещё нет — положение придёт от сервера

		float step = m_Speed * m_Dir * dt;
		m_PredDist = Math.Clamp(m_PredDist + step, 0, t.GetLength());
		m_Dist += step;
		m_Dist += (m_PredDist - m_Dist) * Math.Clamp(dt * 4.0, 0, 1);
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
	}

	// ------------------------------------------------------------------ общее

	override void EOnFrame(IEntity other, float timeSlice)
	{
		if (m_TrackId == 0)
			return;

		if (GetGame().IsServer())
			ServerSimulate(timeSlice);
		else
			ClientSimulate(timeSlice);

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

	// Где стоит водитель (мир) и куда смотрит (yaw в градусах).
	void GetDriverTransform(out vector pos, out float yaw)
	{
		vector local = Vector(0, DECK_HEIGHT, -SEAT_BACK * m_Dir);
		pos = ModelToWorld(local);
		vector dir = GetDirection();
		if (m_Dir < 0)
			dir = dir * -1;
		yaw = dir.VectorToAngles()[0];
	}

	// Текущая подсказка для HUD.
	static string HelpText()
	{
		return "W — качать рычаг, S — тормоз, R — сменить направление (на месте), F — сойти";
	}
}
