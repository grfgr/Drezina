// Прицеп мотодрезины: машина DayZ без водителя (пассажиры садятся как в машину), которую скрипт держит
// на пути сразу за ведущей мотодрезиной. Сцепка — общий номер: m_LinkId у прицепа = m_TrailerLink у
// мотодрезины (номер сохраняется у обоих, после рестарта сцепка восстанавливается).
//
// Положение прицепа считается из положения мотодрезины на каждом кадре — на сервере и на всех клиентах
// (у водителя — прямо из шага мотодрезины), поэтому прицеп не отстаёт и не дёргается.
// Стоп-сигнал горит, когда водитель мотодрезины тормозит (ванильная машина синхронизирует это всем).
class Drezina_Trailer extends CarScript
{
	static ref array<Drezina_Trailer> s_All = new array<Drezina_Trailer>;

	static const string BRAKE_OFF = "Drezina\\data\\textures\\drezina_redglass.rvmat";
	static const string BRAKE_ON = "Drezina\\data\\textures\\drezina_redglass_e.rvmat";
	static const int BRAKE_SEL = 2;   // индекс light_brake_1_2 в hiddenSelections

	int m_LinkId;
	int m_TrackId = -1;
	int m_Face = 1;
	bool m_OffRail;
	float m_LeadHint = -1;    // дистанция ведущей по пути (поиск проекции)
	int m_LeadHintTrack;      // на каком пути эта подсказка
	float m_WheelPhase;
	bool m_GravityOff;
	bool m_BrakeShown;
	Drezina_TailLight m_TailLight;

	void Drezina_Trailer()
	{
		RegisterNetSyncVariableInt("m_LinkId");
		RegisterNetSyncVariableInt("m_TrackId");
		RegisterNetSyncVariableInt("m_Face", -1, 1);
		RegisterNetSyncVariableBool("m_OffRail");
		s_All.Insert(this);
		GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(Follow);
	}

	void ~Drezina_Trailer()
	{
		if (GetGame())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Remove(Follow);
		if (s_All)
			s_All.RemoveItem(this);
		if (m_TailLight)
			m_TailLight.Destroy();
	}

	// ------------------------------------------------------------------ сохранение

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(m_LinkId);
		ctx.Write(m_TrackId);
		ctx.Write(m_Face);
		ctx.Write(m_OffRail);
	}

	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;
		if (!ctx.Read(m_LinkId))
			m_LinkId = 0;
		if (!ctx.Read(m_TrackId))
			m_TrackId = -1;
		if (!ctx.Read(m_Face))
			m_Face = 1;
		if (!ctx.Read(m_OffRail))
			m_OffRail = false;
		return true;
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();
		SetSynchDirty();
	}

	// ------------------------------------------------------------------ экипаж (только пассажиры)

	override int GetAnimInstance()
	{
		return VehicleAnimInstances.HATCHBACK;
	}

	override int GetSeatAnimationType(int posIdx)
	{
		return DayZPlayerConstants.VEHICLESEAT_CODRIVER;
	}

	override bool CrewCanGetThrough(int posIdx)
	{
		return !m_OffRail;
	}

	override bool CanReachSeatFromSeat(int currentSeat, int nextSeat)
	{
		return true;
	}

	override bool CanReachDoorsFromSeat(string pDoorsSelection, int pCurrentSeat)
	{
		return true;
	}

	// у ванильной машины «дотянуться до сиденья» проверяется по точкам seat_con_*, у прицепа их нет:
	// проверяем расстояние до места посадки pos_cargoN
	override bool CanReachSeatFromDoors(string pSeatSelection, vector pFromPos, float pDistance = 1.0)
	{
		string pos = pSeatSelection;
		pos.Replace("seat_", "pos_");
		if (!MemoryPointExists(pos))
			return false;
		vector ws = ModelToWorld(GetMemoryPointPos(pos));
		ws[1] = 0;
		pFromPos[1] = 0;
		return vector.Distance(pFromPos, ws) <= 1.6;
	}

	override float GetTransportCameraDistance()
	{
		return 3.5;
	}

	override vector GetTransportCameraOffset()
	{
		return "0 1.6 0";
	}

	override bool NeedElectricitySourceDevice()
	{
		return false;
	}

	override bool IsVitalSparkPlug()
	{
		return false;
	}

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

	override void SetActions()
	{
		AddAction(ActionGetInTransport);
	}

	// колёса Нивы (невидимые, для физики машины) и бочки не снимаются
	override bool CanReleaseAttachment(EntityAI attachment)
	{
		if (attachment && (attachment.IsInherited(Drezina_TrailerBarrel) || attachment.IsKindOf("HatchbackWheel")))
			return false;
		return super.CanReleaseAttachment(attachment);
	}

	bool IsEmptyCrew()
	{
		for (int i = 0; i < CrewSize(); i++)
		{
			if (CrewMember(i))
				return false;
		}
		return true;
	}

	// все бочки пустые (у пассажирского бочек нет)
	bool StorageEmpty()
	{
		for (int i = 0; i < GetInventory().AttachmentCount(); i++)
		{
			Drezina_TrailerBarrel b = Drezina_TrailerBarrel.Cast(GetInventory().GetAttachmentFromIndex(i));
			if (b && b.GetInventory().GetCargo() && b.GetInventory().GetCargo().GetItemCount() > 0)
				return false;
		}
		return true;
	}

	// ------------------------------------------------------------------ сервер: создание и перестановка

	void ServerInit(int link, int trackId, int face, float d)
	{
		m_LinkId = link;
		m_TrackId = trackId;
		m_Face = face;
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
		GetInventory().CreateAttachment("HatchbackWheel");
		OnServerInit();
		DrezinaTrack t = DrezinaTrackManager.Get().GetTrack(trackId);
		if (t)
			FollowAt(t, d, face, vector.Zero);
		SetSynchDirty();
	}

	// для грузового: бочки
	void OnServerInit()
	{
	}

	void ServerPlace(DrezinaTrack t, float d, int face)
	{
		m_OffRail = false;
		m_Face = face;
		m_LeadHint = -1;
		dBodyActive(this, ActiveState.ACTIVE);
		FollowAt(t, d, face, vector.Zero);
		SetSynchDirty();
	}

	// side — направление вбок в мире (то же, что у дрезины): прицеп сходит в ту же сторону
	bool SideFree(vector side, float off)
	{
		vector mat[4];
		GetTransform(mat);
		vector center = mat[3] + Vector(0, 0.8, 0);
		vector hitPos, hitDir;
		int hitComp;
		return !DayZPhysics.RaycastRV(center, center + side.Normalized() * (off + 0.85), hitPos, hitDir, hitComp, null, null, this, false, false, ObjIntersectGeom);
	}

	void ServerTakeOffRail(vector side, float off)
	{
		vector mat[4];
		GetTransform(mat);
		vector place = mat[3] + side.Normalized() * off;
		vector hitPos, hitDir;
		int hitComp;
		if (DayZPhysics.RaycastRV(place + Vector(0, 1.5, 0), place - Vector(0, 3.0, 0), hitPos, hitDir, hitComp, null, null, this))
			place[1] = hitPos[1] + 0.05;
		mat[3] = place;
		m_OffRail = true;
		SetTransform(mat);
		SetVelocity(this, vector.Zero);
		dBodyEnableGravity(this, true);
		m_GravityOff = false;
		dBodyActive(this, ActiveState.ACTIVE);
		SetSynchDirty();
	}

	// ------------------------------------------------------------------ движение за ведущей

	Drezina_Motor Leader()
	{
		if (m_LinkId == 0)
			return null;
		foreach (Drezina_Motor m : Drezina_Motor.s_All)
		{
			if (m && m.m_TrailerLink == m_LinkId)
				return m;
		}
		return null;
	}

	void FollowAt(DrezinaTrack t, float d, int face, vector vel)
	{
		if (!m_GravityOff)
		{
			m_GravityOff = true;
			dBodyEnableGravity(this, false);
		}
		d = Math.Clamp(d, 0, t.GetLength());
		vector mat[4];
		Drezina_Motor.TrackTransformFace(t, d, face, mat);
		SetTransform(mat);
		// без скорости: иначе физика между кадрами сдвигала прицеп ещё вперёд, а клиент досчитывал
		// движение по скорости — прицеп «обгонял» дрезину. Тело не усыпляем — иначе положение не уходит клиентам.
		SetVelocity(this, vector.Zero);
	}

	void Follow(float dt)
	{
		Drezina_Motor lead = Leader();
		if (!GetGame().IsDedicatedServer())
			UpdateBrakeLight(lead);
		if (!lead || m_OffRail || lead.m_OffRail)
		{
			// снят с рельсов: у клиента снова падает на землю сам
			if (m_OffRail && m_GravityOff && !GetGame().IsServer())
			{
				m_GravityOff = false;
				dBodyEnableGravity(this, true);
			}
			return;
		}
		// клиенты тоже ставят прицеп за ведущей сами, каждый кадр (без гравитации): раньше прицеп у
		// клиента падал под своей тяжестью между пакетами сервера, а сервер его поднимал — дребезг
		DrezinaTrack t = lead.GetTrack();
		if (!t)
			return;
		// где ведущая: проекция её положения на путь (с подсказкой от прошлого кадра)
		float ld = m_LeadHint;
		if (m_LeadHintTrack != t.GetId())
			ld = -1;                     // ведущая перешла на другой путь
		m_LeadHintTrack = t.GetId();
		if (ld < 0)
		{
			float off;
			ld = t.ClosestDistance(lead.GetPosition(), off);
		}
		for (int i = 0; i < 3; i++)
		{
			vector p, dir;
			t.GetPosDir(ld, p, dir);
			ld = Math.Clamp(ld + vector.Dot(lead.GetPosition() - p, dir), 0, t.GetLength());
		}
		m_LeadHint = ld;
		if (GetGame().IsServer() && m_Face != lead.m_Face)
		{
			m_Face = lead.m_Face;
			SetSynchDirty();
		}
		vector vel = GetVelocity(lead);
		DrezinaTrack tt;
		float td;
		int tface;
		lead.TrailerPose(t, ld, tt, td, tface);
		FollowAt(tt, td, tface, vel);
		if (GetGame().IsServer() && tt.GetId() != m_TrackId)
		{
			m_TrackId = tt.GetId();
			SetSynchDirty();
		}
		// колёса крутятся со скоростью ведущей
		if (!GetGame().IsDedicatedServer() && dt > 0 && dt < 0.5)
		{
			float speed = vector.Dot(vel, GetDirection());
			m_WheelPhase += speed * dt / (Math.PI2 * Drezina_Motor.WHEEL_RADIUS);
			m_WheelPhase -= Math.Floor(m_WheelPhase);
			SetAnimationPhase("drezina_wheels", m_WheelPhase);
		}
	}

	// ------------------------------------------------------------------ стоп-сигнал (клиенты)

	void UpdateBrakeLight(Drezina_Motor lead)
	{
		bool lit = lead && lead.BrakeLit() && !m_OffRail;
		if (lit == m_BrakeShown)
			return;
		m_BrakeShown = lit;
		if (lit)
		{
			SetObjectMaterial(BRAKE_SEL, BRAKE_ON);
			if (!m_TailLight)
			{
				m_TailLight = Drezina_TailLight.Cast(ScriptedLightBase.CreateLight(Drezina_TailLight, GetPosition()));
				if (m_TailLight)
					m_TailLight.AttachOnObject(this, GetMemoryPointPos("light_reverse") + Vector(0, 0, -0.15), vector.Zero);
			}
		}
		else
		{
			SetObjectMaterial(BRAKE_SEL, BRAKE_OFF);
			if (m_TailLight)
			{
				m_TailLight.Destroy();
				m_TailLight = null;
			}
		}
	}
}

class Drezina_TrailerPassenger extends Drezina_Trailer {}

class Drezina_TrailerCargo extends Drezina_Trailer
{
	override void OnServerInit()
	{
		for (int i = 0; i < 4; i++)
			GetInventory().CreateAttachment("Drezina_TrailerBarrel");
	}
}

// Бочка грузового прицепа: отдельное хранилище, всегда на прицепе (снять, взять в руки нельзя).
class Drezina_TrailerBarrel extends Container_Base
{
	override bool CanPutInCargo(EntityAI parent)
	{
		return false;
	}

	override bool CanPutIntoHands(EntityAI parent)
	{
		return false;
	}

	override bool CanRemoveFromHands(EntityAI parent)
	{
		return true;
	}

	override bool IsTakeable()
	{
		return false;
	}
}

// Красный отсвет стоп-сигнала прицепа
class Drezina_TailLight extends PointLightBase
{
	void Drezina_TailLight()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(3.5);
		SetBrightnessTo(1.6);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(1.0, 0.1, 0.06);
		SetAmbientColor(1.0, 0.1, 0.06);
	}
}
