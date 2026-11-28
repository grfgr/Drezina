// Управление дрезиной на клиенте водителя. Вызывается из MissionGameplay.OnUpdate.
class DrezinaClientInput
{
	static int s_LastThrottle;

	static void OnBoarded(Drezina_Handcar hc)
	{
		s_LastThrottle = 0;
		// (подсказок игрокам не показываем)
	}

	static void Update(float dt)
	{
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		if (!player)
			return;
		Drezina_Handcar hc = player.m_DrezinaHandcar;
		if (!hc)
		{
			s_LastThrottle = 0;
			return;
		}

		// не реагируем, пока открыто меню / чат / инвентарь
		if (GetGame().GetUIManager().GetMenu())
			return;

		UAInput fwd = GetUApi().GetInputByName("UAMoveForward");
		UAInput back = GetUApi().GetInputByName("UAMoveBack");
		UAInput rev = GetUApi().GetInputByName("UAReloadMagazine");
		UAInput leave = GetUApi().GetInputByName("UAAction");

		int throttle = 0;
		if (fwd && fwd.LocalValue() > 0.5)
			throttle = 1;
		if (back && back.LocalValue() > 0.5)
			throttle = -1;

		if (throttle != s_LastThrottle)
		{
			Print("[Drezina] client throttle " + throttle);
			s_LastThrottle = throttle;
			hc.m_LocalThrottle = throttle;
			GetGame().RPCSingleParam(hc, DrezinaRPC.HC_THROTTLE, new Param1<int>(throttle), true);
		}

		if (rev && rev.LocalPress())
			GetGame().RPCSingleParam(hc, DrezinaRPC.HC_REVERSE, new Param1<int>(0), true);

		if (leave && leave.LocalPress())
		{
			player.m_DrezinaLeftTime = GetGame().GetTime();
			GetGame().RPCSingleParam(hc, DrezinaRPC.HC_LEAVE, new Param1<int>(0), true);
		}
	}
}
