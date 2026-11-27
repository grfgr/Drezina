// Модули задней части мотодрезины: берутся в руки у терминала выдачи и ставятся в слот DrezinaModule.
// Сами по себе ничего не делают — дрезина смотрит, какой модуль стоит (Drezina_Motor.GetModule).
class Drezina_ModuleBase : ItemBase
{
	override bool CanPutInCargo(EntityAI parent)
	{
		return false;
	}
}

class Drezina_ModuleBench : Drezina_ModuleBase
{
}

class Drezina_ModuleBarrels : Drezina_ModuleBase
{
}
