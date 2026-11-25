modded class PlayerBase
{
	Drezina_Handcar m_DrezinaHandcar; // дрезина, на которой игрок стоит водителем

	override void SetActions(out TInputActionMap InputActionMap)
	{
		super.SetActions(InputActionMap);
		AddAction(ActionDrezinaTake, InputActionMap);
		AddAction(ActionDrezinaBoard, InputActionMap);
		AddAction(ActionDrezinaReverse, InputActionMap);
		AddAction(ActionMetroDown, InputActionMap);
		AddAction(ActionMetroUp, InputActionMap);
	}

	bool IsRidingDrezina()
	{
		return DrezinaRideCommand.Cast(GetCommand_Script()) != null;
	}

	override void CommandHandler(float pDt, int pCurrentCommandID, bool pCurrentCommandFinished)
	{
		// Встать на дрезину, как только сервер назначил нас водителем.
		if (m_DrezinaHandcar && pCurrentCommandID == DayZPlayerConstants.COMMANDID_MOVE && !IsRidingDrezina())
		{
			StartCommand_Script(new DrezinaRideCommand(this, m_DrezinaHandcar));
		}

		super.CommandHandler(pDt, pCurrentCommandID, pCurrentCommandFinished);
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);

		if (GetGame().IsServer())
		{
			if (rpc_type == DrezinaRPC.ADMIN_COMMAND)
			{
				Param1<string> p = new Param1<string>("");
				if (ctx.Read(p) && sender && sender.GetPlayer() == this)
				{
					string low = p.param1;
					low.ToLower();
					if (low.IndexOf(DrezinaConst.METRO_PREFIX) == 0)
						DrezinaTunnelManager.Get().ServerOnAdminCommand(sender, p.param1);
					else
						DrezinaTrackManager.Get().ServerOnAdminCommand(sender, p.param1);
				}
			}
		}
		else
		{
			if (rpc_type == DrezinaRPC.CHAT_MSG)
			{
				Param1<string> msg = new Param1<string>("");
				if (ctx.Read(msg))
					GetGame().Chat("[Дрезина] " + msg.param1, "colorImportant");
				return;
			}
			if (!DrezinaTrackManager.Get().ClientOnRPC(rpc_type, ctx))
				DrezinaTunnelManager.Get().ClientOnRPC(rpc_type, ctx);
		}
	}

	override void EEKilled(Object killer)
	{
		if (GetGame().IsServer() && m_DrezinaHandcar)
			m_DrezinaHandcar.ServerClearDriver();
		super.EEKilled(killer);
	}
}
