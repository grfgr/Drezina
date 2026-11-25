// Ванильная темнота и эмбиент подземелья (как в бункере Ливонии) для метро.
// Игра делает «подземелье» зонами UndergroundTrigger: в зоне с EyeAccommodation = 0 глаза
// привыкают к темноте — без фонаря и включённых ламп ничего не видно, играет звук Underground_SoundSet.
// Зоны берутся из UndergroundAreaLoader.m_JsonData (cfgundergroundtriggers.json миссии): мы дописываем
// туда свои записи, ставим на них «носители» UndergroundTriggerCarrier и рассылаем данные клиентам.
class DrezinaUnderground
{
	static const string AMBIENT = "Underground_SoundSet";

	static JsonUndergroundTriggers Data()
	{
		if (!UndergroundAreaLoader.m_JsonData)
			UndergroundAreaLoader.m_JsonData = UndergroundAreaLoader.GetData();
		if (!UndergroundAreaLoader.m_JsonData)
			UndergroundAreaLoader.m_JsonData = new JsonUndergroundTriggers;
		if (!UndergroundAreaLoader.m_JsonData.Triggers)
			UndergroundAreaLoader.m_JsonData.Triggers = new array<ref JsonUndergroundAreaTriggerData>;
		return UndergroundAreaLoader.m_JsonData;
	}

	// Тёмная зона-коробка: центр, размер (ширина X, высота Y, длина Z) и направление «вдоль» (по Z).
	static Object AddZone(vector center, vector size, vector along, string comment)
	{
		JsonUndergroundAreaTriggerData d = new JsonUndergroundAreaTriggerData;
		d.Comment = comment;
		d.CustomSpawn = false;
		d.Position = {center[0], center[1], center[2]};
		float yaw = 0;
		if (along.Length() > 0.01)
			yaw = along.VectorToAngles()[0];
		d.Orientation = {yaw, 0, 0};
		d.Size = {size[0], size[1], size[2]};
		d.EyeAccommodation = 0;
		d.InterpolationSpeed = 1;
		d.UseLinePointFade = false;
		d.AmbientSoundSet = AMBIENT;
		d.Breadcrumbs = new array<ref JsonUndergroundAreaBreadcrumb>;

		JsonUndergroundTriggers data = Data();
		int index = data.Triggers.Count();
		data.Triggers.Insert(d);
		UndergroundTriggerCarrierBase carrier = UndergroundAreaLoader.SpawnTriggerCarrierEx(index, d);
		if (!carrier)
			Print("[Drezina] !!! зона темноты не создана: " + comment);
		return carrier;
	}

	// Клиенты, уже бывшие в игре, получают обновлённый список зон (новые получают его при входе).
	static void SyncAll()
	{
		array<Man> players = new array<Man>;
		GetGame().GetPlayers(players);
		foreach (Man man : players)
		{
			if (man && man.GetIdentity())
				UndergroundAreaLoader.SyncDataSend(man.GetIdentity());
		}
	}
}
