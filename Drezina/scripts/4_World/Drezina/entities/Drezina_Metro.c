// Объекты метро. Все спавнятся сервером из tunnels.json и в CE-хранилище не пишутся.

// Голова бункера с гермодверью на поверхности (модель bunker_entrance).
class Drezina_MetroHatch extends House
{
	int m_TunnelId; // только сервер
	int m_End;      // 0 = вход A, 1 = вход B
}

// Гермодверь изнутри, на верхней площадке лестницы (модель bunker_inner_door).
class Drezina_MetroLadder extends House
{
	int m_TunnelId;
	int m_End;
}

class Drezina_Tunnel10 extends House {}
class Drezina_Tunnel10Tile extends Drezina_Tunnel10 {}
class Drezina_Tunnel10B extends Drezina_Tunnel10 {}
class Drezina_Tunnel10C extends Drezina_Tunnel10 {}
class Drezina_Tunnel10D extends Drezina_Tunnel10 {}
class Drezina_Tunnel10E extends Drezina_Tunnel10 {}
class Drezina_Tunnel10F extends Drezina_Tunnel10 {}
class Drezina_Tunnel10G extends Drezina_Tunnel10 {}
class Drezina_Tunnel2 extends House {}
class Drezina_JunctionHall extends House {}
class Drezina_JunctionWall extends House {}
class Drezina_JunctionPortal extends House {}
class Drezina_MetroStation extends House {}
class Drezina_Rail10 extends House {}
class Drezina_Rail1 extends House {}
class Drezina_BunkerStairs extends House {}
class Drezina_BunkerCorridor extends House {}

// Светильник метро. Горит, только пока работает генератор своей станции (сервер включает,
// состояние синхронизируется). В инвентарь не берётся.
class Drezina_TunnelLamp extends ItemBase
{
	bool m_On;
	Drezina_TunnelLight m_Light;

	void Drezina_TunnelLamp()
	{
		RegisterNetSyncVariableBool("m_On");
	}

	void ServerSetOn(bool on)
	{
		if (m_On == on)
			return;
		m_On = on;
		SetSynchDirty();
		if (!GetGame().IsDedicatedServer())
			UpdateLight();
	}

	override void OnVariablesSynchronized()
	{
		super.OnVariablesSynchronized();
		UpdateLight();
	}

	override void EEInit()
	{
		super.EEInit();
		if (!GetGame().IsDedicatedServer())
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(UpdateLight, 300, false);
	}

	void UpdateLight()
	{
		// стекло светится только когда лампа включена (раньше светилось всегда — жёлтым в темноте)
		if (m_On)
			SetObjectMaterial(0, "Drezina\\data\\textures\\drezina_glass_e.rvmat");
		else
			SetObjectMaterial(0, "Drezina\\data\\textures\\drezina_glass.rvmat");
		if (m_On && !m_Light)
		{
			// светильник настенный: свет перед стеклом
			m_Light = Drezina_TunnelLight.Cast(ScriptedLightBase.CreateLight(Drezina_TunnelLight, GetPosition() + GetDirection() * 0.3));
		}
		else if (!m_On && m_Light)
		{
			m_Light.Destroy();
			m_Light = null;
		}
	}

	override void EEDelete(EntityAI parent)
	{
		if (m_Light)
			m_Light.Destroy();
		super.EEDelete(parent);
	}

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
}

// Мутно-белый свет старой лампы; чуть мерцает (напряжение от генератора гуляет).
class Drezina_TunnelLight extends PointLightBase
{
	void Drezina_TunnelLight()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(13);
		SetBrightnessTo(3.2);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(0.86, 0.88, 0.84);
		SetAmbientColor(0.86, 0.88, 0.84);
		SetFlickerAmplitude(0.08);
		SetFlickerSpeed(2.5);
	}
}

// Аварийный маячок метро: красный плафон на стене, внутри вращается луч (как сигнальная лампа бункера).
// Горит всегда — генераторы больше не нужны. Свет создаётся только на клиентах.
class Drezina_AlarmLamp extends ItemBase
{
	Drezina_AlarmBeam m_Beam;
	Drezina_AlarmGlow m_Glow;
	EffectSound m_Sound;

	// звук вращения: ванильный, если найдётся, иначе свой (моторчик с пощёлкиванием)
	static string s_SoundSet;
	static string PickSound()
	{
		if (s_SoundSet != "")
			return s_SoundSet;
		// всегда свой набор: громкость задана в config.cpp (у ванильных наборов её не поменять)
		s_SoundSet = "Drezina_AlarmLamp_SoundSet";
		Print("[Drezina] звук маячка: " + s_SoundSet);
		return s_SoundSet;
	}
	float m_Angle;

	override void EEInit()
	{
		super.EEInit();
		if (!GetGame().IsDedicatedServer())
		{
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(StartLight, 300, false);
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(Spin);
		}
	}

	void StartLight()
	{
		vector p = GetPosition() - GetDirection() * 0.22;
		m_Glow = Drezina_AlarmGlow.Cast(ScriptedLightBase.CreateLight(Drezina_AlarmGlow, p));
		m_Beam = Drezina_AlarmBeam.Cast(ScriptedLightBase.CreateLight(Drezina_AlarmBeam, p));
		m_Angle = Math.RandomFloat(0, 360);
		m_Sound = SEffectManager.PlaySoundOnObject(PickSound(), this, 0.5, 0.3, true);
	}

	void Spin(float dt)
	{
		if (!m_Beam)
			return;
		m_Angle += dt * 200.0;           // ~0.55 оборота в секунду
		if (m_Angle > 360)
			m_Angle -= 360;
		// луч ходит по кругу в полусфере перед стеной: поворот вокруг оси стены.
		// модель маячка выступает в -GetDirection() (объект ставится «спиной» к залу), поэтому +180°
		vector ori = GetOrientation();
		m_Beam.SetPosition(GetPosition() - GetDirection() * 0.22);
		m_Beam.SetOrientation(Vector(ori[0] + 180.0 + Math.Sin(m_Angle * Math.DEG2RAD) * 80.0, -15.0 + Math.Cos(m_Angle * Math.DEG2RAD) * 25.0, 0));
	}

	override void EEDelete(EntityAI parent)
	{
		if (GetGame())
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Remove(Spin);
		if (m_Beam)
			m_Beam.Destroy();
		if (m_Glow)
			m_Glow.Destroy();
		if (m_Sound)
			m_Sound.SoundStop();
		super.EEDelete(parent);
	}

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
}

// вращающийся красный луч
class Drezina_AlarmBeam extends SpotLightBase
{
	void Drezina_AlarmBeam()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(22);
		SetSpotLightAngle(55);
		SetBrightnessTo(6.0);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(1.0, 0.06, 0.03);
		SetAmbientColor(1.0, 0.06, 0.03);
	}
}

// слабый красный ореол вокруг маячка
class Drezina_AlarmGlow extends PointLightBase
{
	void Drezina_AlarmGlow()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(5);
		SetBrightnessTo(1.2);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(1.0, 0.08, 0.04);
		SetAmbientColor(1.0, 0.08, 0.04);
		SetFlickerAmplitude(0.15);
		SetFlickerSpeed(1.5);
	}
}
