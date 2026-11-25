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
class Drezina_Tunnel10B extends Drezina_Tunnel10 {}
class Drezina_Tunnel10C extends Drezina_Tunnel10 {}
class Drezina_Tunnel10D extends Drezina_Tunnel10 {}
class Drezina_Tunnel2 extends House {}
class Drezina_MetroStation extends House {}
class Drezina_Rail10 extends House {}
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
			m_Light = Drezina_TunnelLight.Cast(ScriptedLightBase.CreateLight(Drezina_TunnelLight, GetPosition() - Vector(0, 0.45, 0)));
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
