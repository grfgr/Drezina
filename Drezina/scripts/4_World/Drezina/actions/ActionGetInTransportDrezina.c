// Ванильное «сесть в машину» проверяет дистанцию до ЦЕНТРА машины (не больше 2 м).
// Места пассажирского прицепа стоят в 3-4 м позади центра мотодрезины, поэтому действие не появлялось.
// Для мотодрезины дистанцию считаем до ближайшей точки посадки (pos_driver / pos_cargoN).
class DrezinaCCTGetIn : CCTObject
{
	override bool Can(PlayerBase player, ActionTarget target)
	{
		Drezina_Motor car;
		if (player && target && Class.CastTo(car, target.GetObject()))
		{
			if (car.IsDamageDestroyed())
				return false;
			vector pp = player.GetPosition();
			if (vector.Distance(pp, car.GetPosition()) <= UAMaxDistances.DEFAULT)
				return true;
			for (int n = 3; n <= 6; n++)
			{
				string pos = "pos_cargo" + n;
				if (car.MemoryPointExists(pos) && vector.Distance(pp, car.ModelToWorld(car.GetMemoryPointPos(pos))) <= UAMaxDistances.DEFAULT)
					return true;
			}
			return false;
		}
		return super.Can(player, target);
	}
}

modded class ActionGetInTransport
{
	override void CreateConditionComponents()
	{
		super.CreateConditionComponents();
		m_ConditionTarget = new DrezinaCCTGetIn(UAMaxDistances.DEFAULT);
	}
}
