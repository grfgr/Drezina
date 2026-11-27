// У терминала выдачи: взять в руки модуль для задней части мотодрезины — лавочку (2 места) или
// две бочки (2 хранилища). Модуль ставится на дрезину как обычное вложение (перетащить в слот
// «Модуль» в инвентаре дрезины). Ненужный модуль можно сдать обратно на терминал.
// (Имена классов остались от прицепов — так не нужно менять регистрацию действий.)
class ActionDrezinaTrailerBase : ActionInteractBase
{
	void ActionDrezinaTrailerBase()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_INTERACTONCE;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	static bool AtDispenser(ActionTarget target)
	{
		return target && Drezina_Dispenser.Cast(target.GetObject()) != null;
	}

	static void GiveModule(PlayerBase player, string type)
	{
		if (!player || player.GetItemInHands())
			return;
		EntityAI it = player.GetHumanInventory().CreateInHands(type);
		if (!it)
			DrezinaTrackManager.Notify(player.GetIdentity(), "Не удалось выдать модуль.");
	}
}

class ActionDrezinaAttachPassenger : ActionDrezinaTrailerBase
{
	void ActionDrezinaAttachPassenger()
	{
		m_Text = "Взять модуль: лавочка";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		return AtDispenser(target) && !player.IsInVehicle() && !player.GetItemInHands();
	}

	override void OnExecuteServer(ActionData action_data)
	{
		GiveModule(action_data.m_Player, "Drezina_ModuleBench");
	}
}

class ActionDrezinaAttachCargo : ActionDrezinaTrailerBase
{
	void ActionDrezinaAttachCargo()
	{
		m_Text = "Взять модуль: две бочки";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		return AtDispenser(target) && !player.IsInVehicle() && !player.GetItemInHands();
	}

	override void OnExecuteServer(ActionData action_data)
	{
		GiveModule(action_data.m_Player, "Drezina_ModuleBarrels");
	}
}

class ActionDrezinaDetachTrailer : ActionDrezinaTrailerBase
{
	void ActionDrezinaDetachTrailer()
	{
		m_Text = "Сдать модуль";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		return AtDispenser(target) && Drezina_ModuleBase.Cast(player.GetItemInHands()) != null;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		EntityAI it = action_data.m_Player.GetItemInHands();
		if (Drezina_ModuleBase.Cast(it))
			GetGame().ObjectDelete(it);
	}
}
