// «Сдать мотодрезину» — только у терминала выдачи: зажать F на терминале. Пустая (без людей и вещей
// в сумке) стоящая мотодрезина в RADIUS метрах от терминала убирается.
class ActionDrezinaReturnCB : ActionContinuousBaseCB
{
	override void CreateActionComponent()
	{
		m_ActionData.m_ActionComponent = new CAContinuousTime(3.0);
	}
}

class ActionDrezinaReturn : ActionContinuousBase
{
	static const float RADIUS = 7.0;

	void ActionDrezinaReturn()
	{
		m_CallbackClass = ActionDrezinaReturnCB;
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONFB_INTERACT;
		m_FullBody = true;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Сдать мотодрезину [зажать]";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	override typename GetInputType()
	{
		return ContinuousInteractActionInput;
	}

	override bool HasTarget()
	{
		return true;
	}

	// мотодрезина, которую можно сдать на этом терминале
	static Drezina_Motor FindReturnable(Drezina_Dispenser disp)
	{
		if (!disp)
			return null;
		foreach (Drezina_Motor car : Drezina_Motor.s_All)
		{
			if (car && vector.Distance(car.GetPosition(), disp.GetPosition()) <= RADIUS && car.CanBeReturned())
				return car;
		}
		return null;
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || player.IsInVehicle())
			return false;
		return FindReturnable(Drezina_Dispenser.Cast(target.GetObject())) != null;
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		Drezina_Motor car = FindReturnable(Drezina_Dispenser.Cast(action_data.m_Target.GetObject()));
		if (!car)
			return;
		if (!car.CargoEmpty())
		{
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Сначала заберите вещи из сумки мотодрезины и бочек прицепа.");
			return;
		}
		car.ServerDetachTrailer();          // прицеп сдаётся вместе с ней
		Print("[Drezina] мотодрезина сдана на терминале");
		DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Мотодрезина сдана.");
		GetGame().ObjectDelete(car);
	}
}
