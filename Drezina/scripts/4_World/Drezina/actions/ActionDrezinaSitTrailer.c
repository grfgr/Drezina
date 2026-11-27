// «Сесть в прицеп»: своё действие без прицела на модель. Ванильное «сесть» ищет место по тому, куда
// смотрит игрок, а места прицепа ему так и не попадались. Здесь: игрок стоит у сиденья пассажирского
// прицепа (в 1.6 м от точки посадки) — садимся на ближайшее свободное место.
class ActionDrezinaSitTrailer : ActionGetInTransport
{
	void ActionDrezinaSitTrailer()
	{
		m_Text = "Сесть в прицеп";
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTNone;
	}

	override bool HasTarget()
	{
		return false;
	}

	static bool FindSeat(PlayerBase player, out Drezina_Motor outCar, out int outSeat)
	{
		outCar = null;
		outSeat = -1;
		if (!player || player.IsInVehicle() || player.GetCommand_Vehicle())
			return false;
		vector pp = player.GetPosition();
		float best = 1.6;
		foreach (Drezina_Motor car : Drezina_Motor.s_All)
		{
			if (!car || car.m_TrailerType != 1 || car.m_OffRail || car.IsDamageDestroyed())
				continue;
			if (vector.Distance(pp, car.GetPosition()) > 8.0)
				continue;
			for (int n = 3; n <= 6; n++)
			{
				if (car.CrewMember(n))
					continue;
				string pos = "pos_cargo" + n;
				if (!car.MemoryPointExists(pos))
					continue;
				vector ws = car.ModelToWorld(car.GetMemoryPointPos(pos));
				if (Math.AbsFloat(ws[1] - pp[1]) > 1.5)
					continue;
				float dist = vector.Distance(Vector(pp[0], 0, pp[2]), Vector(ws[0], 0, ws[2]));
				if (dist < best)
				{
					best = dist;
					outCar = car;
					outSeat = n;
				}
			}
		}
		return outCar != null;
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		Drezina_Motor car;
		int seat;
		return FindSeat(player, car, seat);
	}

	override void OnStart(ActionData action_data)
	{
		Drezina_Motor car;
		int seat;
		if (!FindSeat(action_data.m_Player, car, seat))
		{
			Print("[Drezina] сесть в прицеп: место не найдено (server=" + GetGame().IsServer() + ")");
			return;
		}
		HumanCommandVehicle vehCommand = action_data.m_Player.StartCommand_Vehicle(car, seat, car.GetSeatAnimationType(seat), false);
		Print("[Drezina] сесть в прицеп: место " + seat + ", server=" + GetGame().IsServer() + ", команда=" + (vehCommand != null));
		if (vehCommand)
		{
			vehCommand.SetVehicleType(car.GetAnimInstance());
			action_data.m_Player.GetItemAccessor().HideItemInHands(true);
			if (action_data.m_Player.GetInventory())
				action_data.m_Player.GetInventory().LockInventory(LOCK_FROM_SCRIPT);
		}
	}
}
