// Мотодрезина: настоящая машина DayZ (садятся как в машину, игрок — член экипажа, никакой тряски),
// но едет только по рельсам. Мотор, бензин, свеча, аккумулятор, фары (лампочки H7) и сумка —
// ванильная механика CarScript. Колёс-запчастей у машины нет: после каждого шага физики скрипт сам
// ставит машину на путь и задаёт ей скорость вдоль рельсов (газ/тормоз/передачи берутся у машины).
//
// Места: 0 — водитель (в центре, лицом вперёд), 1 и 2 — пассажиры сзади слева/справа (лицом наружу).
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
	int m_TrailerLink;           // номер сцепки с прицепом (0 — без прицепа); тот же номер у прицепа

	static const float TRAILER_GAP = 2.9;   // между центрами мотодрезины и прицепа (прицеп сзади)

	void Drezina_Motor()
	{
		RegisterNetSyncVariableInt("m_TrackId");
		RegisterNetSyncVariableInt("m_Face", -1, 1);
		RegisterNetSyncVariableBool("m_OffRail");
		RegisterNetSyncVariableInt("m_TrailerLink");

		m_EngineStartOK = "Motorbike_01_engine_start_SoundSet";
		m_EngineStartBattery = "";
		m_EngineStartPlug = "";
		m_EngineStartFuel = "Motorbike_01_engine_failed_start_fuel_SoundSet";
		m_EngineStop = "Motorbike_01_engine_stop_SoundSet";
		m_EngineStopFuel = "Motorbike_01_engine_stop_fuel_SoundSet";

		// фары: свет как у ванильного мотоцикла (у базового профиля машины нет яркости)
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Motorbike_01LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Motorbike_01LightProfileRear()));

		// мотор справа впереди (координаты модели: x вправо, y вверх, z вперёд)
		SetEnginePos("0.22 0.82 0.72");
		s_All.Insert(this);
		GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(WakeWatch);
	}

	void ~Drezina_Motor()
	{
		if (GetGame())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Remove(WakeWatch);
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
		ctx.Write(m_TrailerLink);
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
		if (!ctx.Read(m_TrailerLink))
			m_TrailerLink = 0;
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

	override bool CanReachSeatFromSeat(int currentSeat, int nextSeat)
	{
		return true;
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
		if ((EngineIsOn() && GetThrottle() > 0.01) || GetBrake() > 0.01)
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
		AddAction(ActionSwitchLights);
		AddAction(ActionVehicleHornShort);
		AddAction(ActionVehicleHornLong);
	}

	// аккумулятора нет (как у ванильного мотоцикла) — фары включаются без него.
	// Базовая машина требует аккумулятор, поэтому раньше работал только стоп-сигнал.
	override bool OnBeforeLightOn()
	{
		return true;
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
		// у торцов пути останавливаемся за 1.6 м (там тупиковый упор станции)
		float lo = Math.Min(END_GAP, t.GetLength() * 0.5);
		float hi = Math.Max(t.GetLength() - END_GAP, lo);
		Drezina_Trailer tr = Trailer();
		if (tr && !tr.m_OffRail)
		{
			// прицеп сзади (на стороне -нос): ему тоже нужно место до торца
			if (m_Face > 0)
				lo = Math.Min(lo + TRAILER_GAP, hi);
			else
				hi = Math.Max(hi - TRAILER_GAP, lo);
		}
		if (nd <= lo || nd >= hi)
		{
			nd = Math.Clamp(nd, lo, hi);
			v = 0;
		}
		m_DistHint = nd;

		vector mat[4];
		TrackTransform(t, nd, mat);
		SetTransform(mat);
		SetVelocity(this, mat[2] * v);
		// прицеп ставим в тот же кадр — на клиенте водителя он едет вплотную, без отставания
		if (tr && !tr.m_OffRail)
			tr.FollowAt(t, nd - m_Face * TRAILER_GAP, m_Face, mat[2] * v);

		// стоим и газа нет — усыпляем физику: тело больше не шевелится (иначе дрожь на месте)
		if (v == 0 && throttle <= 0.01)
		{
			m_StillTime += dt;
			if (m_StillTime > 0.3 && !m_Sleeping)
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
		Drezina_Trailer own = Trailer();
		if (own && !own.m_OffRail && moveDir == -m_Face)
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
		foreach (Drezina_Trailer ot : Drezina_Trailer.s_All)
		{
			if (!ot || ot == own || ot.m_OffRail || ot.m_TrackId != m_TrackId)
				continue;
			float otd = ProjectDistOf(t, ot.GetPosition());
			float aheadT = (otd - head) * moveDir;
			if (aheadT > 0 && aheadT < clearance)
				return true;
		}
		return false;
	}

	// ------------------------------------------------------------------ прицеп

	Drezina_Trailer Trailer()
	{
		if (m_TrailerLink == 0)
			return null;
		foreach (Drezina_Trailer tr : Drezina_Trailer.s_All)
		{
			if (tr && tr.m_LinkId == m_TrailerLink)
				return tr;
		}
		return null;
	}

	bool HasTrailer()
	{
		return Trailer() != null;
	}

	// прицепить у терминала: прицеп встаёт сзади на путь; если сзади мало места — мотодрезина откатывается вперёд
	bool ServerAttachTrailer(string type)
	{
		DrezinaTrack t = GetTrack();
		if (!t || m_OffRail || HasTrailer())
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

		float td = d - m_Face * TRAILER_GAP;
		vector tmat[4];
		TrackTransformFace(t, td, m_Face, tmat);
		Drezina_Trailer tr = Drezina_Trailer.Cast(GetGame().CreateObjectEx(type, tmat[3], ECE_CREATEPHYSICS | ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN, RF_DEFAULT));
		if (!tr)
		{
			Print("[Drezina] !!! прицеп не создан: " + type);
			return false;
		}
		int link = Math.RandomIntInclusive(1, 2000000000);
		m_TrailerLink = link;
		tr.ServerInit(link, m_TrackId, m_Face, td);
		SetSynchDirty();
		Print("[Drezina] прицеплен " + type + ", сцепка " + link);
		return true;
	}

	void ServerDetachTrailer()
	{
		Drezina_Trailer tr = Trailer();
		if (tr)
			GetGame().ObjectDelete(tr);
		m_TrailerLink = 0;
		SetSynchDirty();
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
		Drezina_Trailer tr = Trailer();
		if (tr && !tr.IsEmptyCrew())
			return false;
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
		Drezina_Trailer tr = Trailer();
		if (tr)
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
		if (tr)
			tr.ServerPlace(t, d - m_Face * TRAILER_GAP, m_Face);
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
		Drezina_Trailer tr = Trailer();
		for (int k = 0; k < 2; k++)
		{
			sgn = 1;
			if (k == 1)
				sgn = -1;
			vector side = mat[0] * sgn;
			// луч до дальнего борта дрезины в стоящем положении (+0.9 м); с прицепом — и у прицепа
			if (DayZPhysics.RaycastRV(center, center + side * (off + 0.9), hitPos, hitDir, hitComp, null, null, this))
				continue;
			if (tr && !tr.SideFree(sgn, off))
				continue;
			place = mat[3] + side * off;
			break;
		}
		if (place == vector.Zero)
			return false;
		if (tr)
			tr.ServerTakeOffRail(sgn, off);
		// земля под новым местом
		vector top = place + Vector(0, 1.5, 0);
		if (DayZPhysics.RaycastRV(top, place - Vector(0, 3.0, 0), hitPos, hitDir, hitComp, null, null, this))
			place[1] = hitPos[1] + 0.05;
		mat[3] = place;
		m_OffRail = true;
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		m_Sleeping = true;
		dBodyActive(this, ActiveState.INACTIVE);
		SetSynchDirty();
		Print("[Drezina] motor: снята с рельсов");
		return true;
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
		Drezina_Trailer tr = Trailer();
		if (tr)
		{
			tr.m_TrackId = m_TrackId;
			tr.ServerPlace(t, d - m_Face * TRAILER_GAP, m_Face);
		}
		SetSynchDirty();
		Print("[Drezina] motor: поставлена на путь #" + found);
		return true;
	}

	bool CanBeReturned()
	{
		Drezina_Trailer trl = Trailer();
		if (trl && !trl.IsEmptyCrew())
			return false;
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
		Drezina_Trailer tr = Trailer();
		if (tr && !tr.StorageEmpty())
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
