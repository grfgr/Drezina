// «Открыть гермодверь» у входа в бункер: анимация открывания двери, скрежет — и игрок за дверью,
// на верхней площадке лестницы. Дальше 4 марша вниз пешком.
class ActionMetroDown extends ActionInteractBase
{
	void ActionMetroDown()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Открыть гермодверь";
	}

	override void OnStartClient(ActionData action_data)
	{
		super.OnStartClient(action_data);
		if (action_data.m_Target && action_data.m_Target.GetObject())
		{
			EffectSound snd = SEffectManager.PlaySoundOnObject("Drezina_Door_SoundSet", action_data.m_Target.GetObject());
			if (snd)
				snd.SetAutodestroy(true);
		}
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(4.0);
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		return target && !player.m_DrezinaHandcar && Drezina_MetroHatch.Cast(target.GetObject()) != null;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_MetroHatch h = Drezina_MetroHatch.Cast(action_data.m_Target.GetObject());
		if (h)
			DrezinaTunnelManager.Get().ServerTeleport(action_data.m_Player, h.m_TunnelId, h.m_End, true);
	}
}

// «Открыть гермодверь» изнутри, на верхней площадке лестницы — выход на поверхность.
class ActionMetroUp extends ActionInteractBase
{
	void ActionMetroUp()
	{
		m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW;
		m_StanceMask = DayZPlayerConstants.STANCEMASK_ERECT | DayZPlayerConstants.STANCEMASK_CROUCH;
		m_Text = "Выйти наружу";
	}

	override void OnStartClient(ActionData action_data)
	{
		super.OnStartClient(action_data);
		if (action_data.m_Target && action_data.m_Target.GetObject())
		{
			EffectSound snd = SEffectManager.PlaySoundOnObject("Drezina_Door_SoundSet", action_data.m_Target.GetObject());
			if (snd)
				snd.SetAutodestroy(true);
		}
	}

	override void CreateConditionComponents()
	{
		m_ConditionItem = new CCINone;
		m_ConditionTarget = new CCTObject(3.0);
	}

	override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
	{
		return target && !player.m_DrezinaHandcar && Drezina_MetroLadder.Cast(target.GetObject()) != null;
	}

	override void OnExecuteServer(ActionData action_data)
	{
		Drezina_MetroLadder l = Drezina_MetroLadder.Cast(action_data.m_Target.GetObject());
		if (l)
			DrezinaTunnelManager.Get().ServerTeleport(action_data.m_Player, l.m_TunnelId, l.m_End, false);
	}
}
