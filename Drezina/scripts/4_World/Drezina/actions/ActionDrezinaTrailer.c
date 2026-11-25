// У терминала выдачи: к стоящей рядом пустой мотодрезине прицепить ОДИН прицеп — пассажирский или грузовой
// (состав из нескольких прицепов не собирается), или отцепить его (если в нём никого и бочки пустые).
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

	// мотодрезина у этого терминала: стоит, пустая, на рельсах
	static Drezina_Motor CarAt(ActionTarget target)
	{
		if (!target)
			return null;
		Drezina_Dispenser disp = Drezina_Dispenser.Cast(target.GetObject());
		if (!disp)
			return null;
		foreach (Drezina_Motor car : Drezina_Motor.s_All)
		{
			if (car && !car.m_OffRail && car.GetTrack() && vector.Distance(car.GetPosition(), disp.GetPosition()) <= ActionDrezinaReturn.RADIUS && car.CanBeReturned())
				return car;
		}
		return null;
	}
}

class ActionDrezinaAttachPassenger : ActionDrezinaTrailerBase
{
	void ActionDrezinaAttachPassenger()
	{
		m_Text = "Прицепить пассажирский прицеп";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = CarAt(target);
		return car && !player.IsInVehicle() && car.m_TrailerLink == 0;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_Motor car = CarAt(action_data.m_Target);
		if (car && car.m_TrailerLink == 0 && !car.ServerAttachTrailer("Drezina_TrailerPassenger"))
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Не удалось прицепить (мало места на пути?).");
	}
}

class ActionDrezinaAttachCargo : ActionDrezinaTrailerBase
{
	void ActionDrezinaAttachCargo()
	{
		m_Text = "Прицепить грузовой прицеп";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = CarAt(target);
		return car && !player.IsInVehicle() && car.m_TrailerLink == 0;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_Motor car = CarAt(action_data.m_Target);
		if (car && car.m_TrailerLink == 0 && !car.ServerAttachTrailer("Drezina_TrailerCargo"))
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Не удалось прицепить (мало места на пути?).");
	}
}

class ActionDrezinaDetachTrailer : ActionDrezinaTrailerBase
{
	void ActionDrezinaDetachTrailer()
	{
		m_Text = "Отцепить прицеп";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = CarAt(target);
		return car && !player.IsInVehicle() && car.m_TrailerLink != 0;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_Motor car = CarAt(action_data.m_Target);
		if (!car)
			return;
		Drezina_Trailer tr = car.Trailer();
		if (tr && !tr.StorageEmpty())
		{
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Сначала освободите бочки прицепа.");
			return;
		}
		car.ServerDetachTrailer();
		DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Прицеп отцеплен.");
	}
}
