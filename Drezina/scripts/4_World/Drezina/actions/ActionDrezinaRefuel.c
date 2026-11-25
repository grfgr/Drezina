// «Заправить мотодрезину»: канистра (или любая ёмкость) с бензином в руках, смотреть на мотодрезину,
// зажать ЛКМ (как ванильная заправка машины). Переливает сразу всё, что влезет в бак.
class ActionDrezinaRefuelCB : ActionContinuousBaseCB
{
	override void CreateActionComponent()
	{
		m_ActionData.m_ActionComponent = new CAContinuousTime(3.0);
	}
}

class ActionDrezinaRefuel : ActionContinuousBase
{
	void ActionDrezinaRefuel()
	{
		m_CallbackClass = ActionDrezinaRefuelCB;
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONFB_INTERACT;
		m_FullBody = true;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Заправить мотодрезину";
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

	static bool HasGasoline(ItemBase item)
	{
		return item && item.GetQuantity() > 0 && item.GetLiquidType() == LIQUID_GASOLINE;
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		if (!target || !HasGasoline(item) || player.IsInVehicle())
			return false;
		Drezina_Motor car = Drezina_Motor.Cast(target.GetObject());
		if (!car)
			car = Drezina_Motor.Cast(target.GetParent());
		return car && car.GetFluidFraction(CarFluid.FUEL) < 0.99;
	}

	override void OnFinishProgressServer(ActionData action_data)
	{
		ItemBase item = action_data.m_MainItem;
		Drezina_Motor car = Drezina_Motor.Cast(action_data.m_Target.GetObject());
		if (!car)
			car = Drezina_Motor.Cast(action_data.m_Target.GetParent());
		if (!car || !HasGasoline(item))
			return;
		float cap = car.GetFluidCapacity(CarFluid.FUEL);
		float room = cap * (1.0 - car.GetFluidFraction(CarFluid.FUEL));     // литры
		float have = item.GetQuantity() / 1000.0;                             // мл -> л
		float liters = Math.Min(room, have);
		if (liters <= 0)
			return;
		car.Fill(CarFluid.FUEL, liters);
		item.AddQuantity(-liters * 1000.0);
		Print("[Drezina] заправка: +" + liters + " л, бак " + (car.GetFluidFraction(CarFluid.FUEL) * cap) + " / " + cap);
		DrezinaTrackManager.Notify(action_data.m_Player.GetIdentity(), "Залито " + Math.Round(liters * 10) / 10 + " л. В баке " + Math.Round(car.GetFluidFraction(CarFluid.FUEL) * cap * 10) / 10 + " из " + cap + " л.");
	}
}

// действие доступно с бензином в руках: канистры и бутылки
modded class Bottle_Base
{
	override void SetActions()
	{
		super.SetActions();
		AddAction(ActionDrezinaRefuel);
	}
}
