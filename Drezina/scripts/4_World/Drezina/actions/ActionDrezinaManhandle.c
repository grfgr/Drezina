// Руками с мотодрезиной (стоит, мотор заглушен, никого нет): зажать F, глядя на неё.
//   «Развернуть»          — нос в другую сторону (передача вперёд одна, назад только медленно);
//   «Снять с рельсов»     — сдвинуть вбок от пути, чтобы встречная проехала (разъезд);
//   «Поставить на рельсы» — обратно на ближайший путь.
class ActionDrezinaManhandleCB : ActionContinuousBaseCB
{
	override void CreateActionComponent()
	{
		m_ActionData.m_ActionComponent = new CAContinuousTime(3.0);
	}
}

class ActionDrezinaManhandleBase : ActionContinuousBase
{
	void ActionDrezinaManhandleBase()
	{
		m_CallbackClass = ActionDrezinaManhandleCB;
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONFB_INTERACT;
		m_FullBody = true;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.5);
	}

	override typename GetInputType()
	{
		return ContinuousInteractActionInput;
	}

	override bool HasTarget()
	{
		return true;
	}

	Drezina_Motor Car(ActionTarget target)
	{
		if (!target)
			return null;
		Drezina_Motor car = Drezina_Motor.Cast(target.GetObject());
		if (!car)
			car = Drezina_Motor.Cast(target.GetParent());
		return car;
	}
}

class ActionDrezinaTurnAround : ActionDrezinaManhandleBase
{
	void ActionDrezinaTurnAround()
	{
		m_Text = "Развернуть мотодрезину [зажать]";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = Car(target);
		return car && !player.IsInVehicle() && car.CanTurnAround();
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		Drezina_Motor car = Car(action_data.m_Target);
		if (car && car.CanTurnAround() && !car.ServerTurnAround())
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Мало места для прицепа: отъедьте от конца пути.");
	}
}

class ActionDrezinaOffRail : ActionDrezinaManhandleBase
{
	void ActionDrezinaOffRail()
	{
		m_Text = "Снять с рельсов [зажать]";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = Car(target);
		return car && !player.IsInVehicle() && car.CanTakeOffRail();
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		Drezina_Motor car = Car(action_data.m_Target);
		if (car && car.CanTakeOffRail() && !car.ServerTakeOffRail())
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Некуда сдвинуть: с обеих сторон стена.");
	}
}

class ActionDrezinaOnRail : ActionDrezinaManhandleBase
{
	void ActionDrezinaOnRail()
	{
		m_Text = "Поставить на рельсы [зажать]";
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car = Car(target);
		return car && !player.IsInVehicle() && car.CanPutOnRail();
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		Drezina_Motor car = Car(action_data.m_Target);
		if (car && car.CanPutOnRail() && !car.ServerPutOnRail())
			DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Рядом нет пути (подкатите ближе, до 4 м).");
	}
}
