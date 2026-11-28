// «Починить мотодрезину»: горелка с газовым баллоном в руках, смотреть на мотодрезину, зажать ЛКМ.
// Через 15 с дрезина полностью цела (корпус и мотор). Пока идёт ремонт, горелка горит и тратит газ.
class ActionDrezinaRepairCB : ActionContinuousBaseCB
{
	override void CreateActionComponent()
	{
		m_ActionData.m_ActionComponent = new CAContinuousTime(15.0);
	}
}

class ActionDrezinaRepair : ActionContinuousBase
{
	void ActionDrezinaRepair()
	{
		m_CallbackClass = ActionDrezinaRepairCB;
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONFB_INTERACT;
		m_FullBody = true;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Починить мотодрезину";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINonRuined;
		m_ConditionTarget = new CCTObject(3.5);
	}

	override bool HasTarget()
	{
		return true;
	}

	static Drezina_Motor CarOf(ActionTarget target)
	{
		if (!target)
			return null;
		Drezina_Motor car = Drezina_Motor.Cast(target.GetObject());
		if (!car)
			car = Drezina_Motor.Cast(target.GetParent());
		return car;
	}

	static bool TorchReady(ItemBase item)
	{
		return item && item.IsInherited(Blowtorch) && item.GetCompEM() && item.GetCompEM().CanWork();
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (player.IsInVehicle() || !TorchReady(item))
			return false;
		Drezina_Motor car = CarOf(target);
		// уровень здоровья и «сломана» синхронизируются на клиент (GetHealth там вызывать нельзя)
		return car && (car.IsBroken() || car.GetHealthLevel("") > GameConstants.STATE_PRISTINE);
	}

	override void OnStartServer(ActionData action_data)
	{
		super.OnStartServer(action_data);
		if (action_data.m_MainItem && action_data.m_MainItem.GetCompEM())
			action_data.m_MainItem.GetCompEM().SwitchOn();
	}

	override void OnEndServer(ActionData action_data)
	{
		if (action_data.m_MainItem && action_data.m_MainItem.GetCompEM())
			action_data.m_MainItem.GetCompEM().SwitchOff();
		super.OnEndServer(action_data);
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		Drezina_Motor car = CarOf(action_data.m_Target);
		if (!car)
			return;
		car.SetHealthMax("", "");
		car.SetHealthMax("Engine", "");
		car.SetHealthMax("Chassis", "");
		car.SetHealthMax("FuelTank", "");
		car.IsBroken();   // обновить синхронизированный флаг «сломана»
		Print("[Drezina] мотодрезина починена горелкой");
		DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Мотодрезина починена.");
	}
}

modded class Blowtorch
{
	override void SetActions()
	{
		super.SetActions();
		AddAction(ActionDrezinaRepair);
	}
}
