modded class PlayerBase
{
	Drezina_Handcar m_DrezinaHandcar; // дрезина, на которой игрок стоит водителем
	bool m_DrezinaInputOff;           // (старое) управление было выключено целиком
	bool m_DrezinaMoveBlocked;        // ходьба и оружие заблокированы на время езды
	int m_DrezinaLeftTime = -100000;  // когда сошёл с дрезины (мс игрового времени)
	int m_DrezinaNextRequest;         // клиент: когда снова запросить пути и метро у сервера

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
		AddAction(ActionDrezinaReturn, InputActionMap);
	}

	bool IsRidingDrezina()
	{
		return DrezinaRideCommand.Cast(GetCommand_Script()) != null;
	}

	// Клиент сам просит у сервера пути и метро, когда его персонаж уже есть. Рассылка при подключении
	// уходила раньше, чем персонаж появлялся на клиенте, и терялась: без путей дрезина у клиента ехала
	// мимо рельсов и расходилась с сервером, а у КПК не было данных для карты метро.
	void DrezinaRequestData()
	{
		if (GetGame().IsServer() || DrezinaTrackManager.s_ClientGotData || GetGame().GetPlayer() != this)
			return;
		int now = GetGame().GetTime();
		if (now < m_DrezinaNextRequest)
			return;
		m_DrezinaNextRequest = now + 5000;
		GetGame().RPCSingleParam(this, DrezinaRPC.REQUEST_ALL, new Param1<int>(0), true);
		Print("[Drezina] клиент: запрос путей и метро у сервера");
	}

	override void CommandHandler(float pDt, int pCurrentCommandID, bool pCurrentCommandFinished)
	{
		DrezinaRequestData();
		bool riding = m_DrezinaHandcar != null;

		// управление персонажем не отключаем (иначе не работает обзор мышью):
		// ходьбу игнорирует команда езды, удары и падения на паузе (ниже).
		// Если старая версия мода успела отключить ввод — включаем обратно.
		if (m_DrezinaInputOff && GetInputController())
		{
			GetInputController().SetDisabled(false);
			m_DrezinaInputOff = false;
		}
		// на дрезине блокируем только ходьбу и поднятие оружия, обзор мышью остаётся
		if (riding != m_DrezinaMoveBlocked && GetInputController())
		{
			GetInputController().OverrideMovementSpeed(riding, 0);
			GetInputController().OverrideMovementAngle(riding, 0);
			GetInputController().OverrideRaise(riding, false);
			m_DrezinaMoveBlocked = riding;
		}

		if (riding && IsAlive())
		{
			// встать на дрезину, как только сервер назначил нас водителем
			if (!IsRidingDrezina())
			{
				if (pCurrentCommandID == DayZPlayerConstants.COMMANDID_MOVE)
					StartCommand_Script(new DrezinaRideCommand(this, m_DrezinaHandcar));
				else
					super.CommandHandler(pDt, pCurrentCommandID, pCurrentCommandFinished);
				return;
			}
			// пока стоим на дрезине, ванильная логика персонажа на паузе: иначе она считает,
			// что под ногами нет земли, запускает падение и обрывает команду езды (рывки),
			// а логика ударов падает без команды ходьбы
			return;
		}

		super.CommandHandler(pDt, pCurrentCommandID, pCurrentCommandFinished);
	}

	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, rpc_type, ctx);

		if (GetGame().IsServer())
		{
			if (rpc_type == DrezinaRPC.REQUEST_ALL)
			{
				if (sender && sender.GetPlayer() == this)
				{
					DrezinaTrackManager.Get().SendAllTo(sender);
					DrezinaTunnelManager.Get().SendAllTo(sender);
				}
				return;
			}
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
