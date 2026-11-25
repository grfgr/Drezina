// Каждое действие должно быть зарегистрировано здесь, иначе AddAction в PlayerBase.SetActions
// падает (NULL pointer) и действия не появляются.
modded class ActionConstructor
{
	override void RegisterActions(TTypenameArray actions)
	{
		super.RegisterActions(actions);
		actions.Insert(ActionDrezinaTake);
		actions.Insert(ActionDrezinaBoard);
		actions.Insert(ActionDrezinaReverse);
		actions.Insert(ActionMetroDown);
		actions.Insert(ActionMetroUp);
		actions.Insert(ActionDrezinaReturn);
		actions.Insert(ActionDrezinaRefuel);
		actions.Insert(ActionDrezinaTurnAround);
		actions.Insert(ActionDrezinaOffRail);
		actions.Insert(ActionDrezinaOnRail);
	}
}
