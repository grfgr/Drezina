modded class MissionServer
{
	override void OnInit()
	{
		super.OnInit();
		// чуть позже, чтобы мир и CE точно успели подняться
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(DrezinaServerInit, 2000, false);
	}

	void DrezinaServerInit()
	{
		DrezinaTrackManager.Get().ServerInit();
		DrezinaTunnelManager.Get().ServerInit(); // после путей: тоннель ссылается на свой путь

		// игроки, зашедшие раньше инициализации
		array<Man> players = new array<Man>;
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			if (m && m.GetIdentity())
				DrezinaTrackManager.Get().SendAllTo(m.GetIdentity());
		}
	}

	override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
	{
		super.InvokeOnConnect(player, identity);
		DrezinaTrackManager.Get().SendAllTo(identity);
	}
}
