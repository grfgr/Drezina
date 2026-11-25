// «Взять дрезину» у станции выдачи: дрезина ставится на рельсы у торца пути и игрок сразу встаёт за рычаг.
class ActionDrezinaTake extends ActionInteractBase
{
	void ActionDrezinaTake()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_INTERACTONCE;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Взять дрезину";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || player.m_DrezinaHandcar || player.DrezinaBoardCooldown())
			return false;
		return Drezina_Dispenser.Cast(target.GetObject()) != null;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Object obj = action_data.m_Target.GetObject();
		Print("[Drezina] ActionDrezinaTake: цель " + obj);
		Drezina_Dispenser disp = Drezina_Dispenser.Cast(obj);
		DrezinaTrackManager.Get().ServerTakeHandcar(action_data.m_Player, disp);
	}
}

// «Встать за рычаг» у уже стоящей свободной дрезины.
class ActionDrezinaBoard extends ActionInteractBase
{
	void ActionDrezinaBoard()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_INTERACTONCE;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Встать за рычаг";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || player.m_DrezinaHandcar || player.DrezinaBoardCooldown())
			return false;
		Drezina_Handcar hc = Drezina_Handcar.Cast(target.GetObject());
		return hc && !hc.HasDriver() && hc.m_SyncSpeed < 0.5;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_Handcar hc = Drezina_Handcar.Cast(action_data.m_Target.GetObject());
		if (hc && !hc.HasDriver() && !action_data.m_Player.m_DrezinaHandcar && !action_data.m_Player.DrezinaBoardCooldown())
			hc.ServerSetDriver(action_data.m_Player);
	}
}

// «Развернуть дрезину» снаружи (сменить направление, пока на ней никого нет).
class ActionDrezinaReverse extends ActionInteractBase
{
	void ActionDrezinaReverse()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_INTERACTONCE;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Сменить направление";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || player.m_DrezinaHandcar || player.DrezinaBoardCooldown())
			return false;
		Drezina_Handcar hc = Drezina_Handcar.Cast(target.GetObject());
		return hc && !hc.HasDriver() && hc.m_SyncSpeed < 0.5;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_Handcar hc = Drezina_Handcar.Cast(action_data.m_Target.GetObject());
		if (hc && !hc.HasDriver())
			hc.ServerPlaceOnTrack(hc.m_TrackId, hc.m_Dist, -hc.m_Dir);
	}
}
