// «Сдать дрезину»: стоящую пустую дрезину рядом со станцией выдачи можно убрать.
class ActionDrezinaReturn extends ActionInteractBase
{
	static const float NEAR_DISPENSER = 15.0;

	void ActionDrezinaReturn()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_INTERACTONCE;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Сдать дрезину";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	static bool NearDispenser(Object hc)
	{
		array<Object> objs = new array<Object>;
		GetGame().GetObjectsAtPosition(hc.GetPosition(), NEAR_DISPENSER, objs, null);
		foreach (Object o : objs)
		{
			if (Drezina_Dispenser.Cast(o))
				return true;
		}
		return false;
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || player.m_DrezinaHandcar || player.IsInVehicle())
			return false;
		Drezina_Motor car = Drezina_Motor.Cast(target.GetObject());
		if (car)
			return car.CanBeReturned() && NearDispenser(car);
		Drezina_Handcar hc = Drezina_Handcar.Cast(target.GetObject());
		return hc && !hc.HasDriver() && hc.m_SyncSpeed < 0.3 && NearDispenser(hc);
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Object obj = action_data.m_Target.GetObject();
		Drezina_Motor car = Drezina_Motor.Cast(obj);
		if (car)
		{
			if (!car.CargoEmpty())
			{
				DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Сначала заберите вещи из сумки мотодрезины.");
				return;
			}
			if (car.CanBeReturned() && NearDispenser(car))
			{
				Print("[Drezina] мотодрезина сдана");
				GetGame().ObjectDelete(car);
			}
			return;
		}
		Drezina_Handcar hc = Drezina_Handcar.Cast(obj);
		if (hc && !hc.HasDriver() && hc.m_Speed < 0.3 && NearDispenser(hc))
		{
			Print("[Drezina] дрезина сдана");
			GetGame().ObjectDelete(hc);
		}
	}
}
