// Объекты метро. Все спавнятся сервером из tunnels.json и в CE-хранилище не пишутся.

// Павильон-спуск на поверхности.
class Drezina_MetroHatch extends House
{
	int m_TunnelId; // только сервер
	int m_End;      // 0 = вход A, 1 = вход B
}

// Лестница наверх на подземной станции.
class Drezina_MetroLadder extends House
{
	int m_TunnelId;
	int m_End;
}

class Drezina_Tunnel10 extends House {}
class Drezina_Tunnel2 extends House {}
class Drezina_MetroStation extends House {}
class Drezina_Rail10 extends House {}

// Светильник в своде тоннеля: модель + настоящий источник света на клиенте.
class Drezina_TunnelLight extends PointLightBase
{
	void Drezina_TunnelLight()
	{
		SetVisibleDuringDaylight(true);
		SetRadiusTo(14);
		SetBrightnessTo(4.5);
		SetCastShadow(false);
		SetFlareVisible(false);
		SetDiffuseColor(1.0, 0.82, 0.55);
		SetAmbientColor(1.0, 0.82, 0.55);
	}
}

class Drezina_TunnelLamp extends House
{
	Drezina_TunnelLight m_Light;

	override void EEInit()
	{
		super.EEInit();
		if (!GetGame().IsDedicatedServer())
			GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(CreateLight, 200, false);
	}

	void CreateLight()
	{
		if (!m_Light)
			m_Light = Drezina_TunnelLight.Cast(ScriptedLightBase.CreateLight(Drezina_TunnelLight, GetPosition() - Vector(0, 0.35, 0)));
	}

	override void EEDelete(EntityAI parent)
	{
		if (m_Light)
			m_Light.Destroy();
		super.EEDelete(parent);
	}
}
