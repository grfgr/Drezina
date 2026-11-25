modded class PlayerBase
{
	Drezina_Handcar m_DrezinaHandcar; // дрезина, на которой игрок стоит водителем
	bool m_DrezinaInputOff;           // обычное управление персонажем выключено на время езды
	int m_DrezinaLeftTime = -100000;  // когда сошёл с дрезины (мс игрового времени)

	// сразу после схода нельзя снова встать за рычаг: то же нажатие F запускало «Встать за рычаг»
	bool DrezinaBoardCooldown()
	{
		return GetGame().GetTime() - m_DrezinaLeftTime < 1500;
	}

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

		// на дрезине обычное управление (ходьба, удары, оружие) выключено: ваниль иначе пытается
		// обработать удар без команды ходьбы. Клавиши дрезины читаются отдельно (DrezinaClientInput).
		bool riding = m_DrezinaHandcar != null;
		if (riding != m_DrezinaInputOff && GetInputController())
		{
			GetInputController().SetDisabled(riding);
			m_DrezinaInputOff = riding;
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
