// Станция выдачи дрезин у конца пути. Спавнится сервером, в мире не сохраняется
// (пересоздаётся из tracks.json при каждом старте).
class Drezina_Dispenser extends House
{
	int  m_TrackId;   // заполняется только на сервере
	bool m_AtStart;
}

// Звено рельсов, 2 м. Чистая геометрия, логики нет.
class Drezina_Rail extends House
{
}
