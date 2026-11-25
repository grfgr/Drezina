modded class MissionGameplay
{
	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		DrezinaClientInput.Update(timeslice);
	}
}

// Перехват команд "/rail ..." из чата: в общий чат не уходят, отправляются серверу.
modded class ChatInputMenu
{
	override bool OnChange(Widget w, int x, int y, bool finished)
	{
		if (finished && m_edit_box)
		{
			string text = m_edit_box.GetText();
			string low = text;
			low.ToLower();
			if (low.IndexOf(DrezinaConst.CHAT_PREFIX) == 0 || low.IndexOf(DrezinaConst.METRO_PREFIX) == 0)
			{
				PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
				if (player)
					GetGame().RPCSingleParam(player, DrezinaRPC.ADMIN_COMMAND, new Param1<string>(text), true);
				m_edit_box.SetText("");
				m_close_timer.Run(0.1, this, "Close");
				return true;
			}
		}
		return super.OnChange(w, x, y, finished);
	}
}
