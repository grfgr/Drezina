// Метро: данные тоннеля (tunnels.json). Вся геометрия восстанавливается из Route, Offset и FloorY.
class DrezinaTunnelData
{
	int    Id;
	ref array<vector> Route = new array<vector>; // точки на поверхности: вход A, повороты..., вход B
	vector Offset;   // сдвиг подземной части по X/Z относительно поверхности (0 — прямо под маршрутом)
	float  FloorY;   // высота пола тоннеля
	bool   Zone;     // true — тоннель в отдельной локации за картой
	int    TrackId;  // путь (DrezinaTrack) внутри тоннеля
	vector FaceA;    // куда смотрит вход A (взгляд админа при /metro a | /rail start); 0 — вдоль линии
	vector FaceB;    // куда смотрит выход B
	int    JoinA;    // конец A подключён к линии JoinA (Т-развязка вместо станции), 0 — обычная станция
	int    JoinB;
	vector JoinPA;   // точка на оси той линии, к которой подключён конец
	vector JoinPB;
}

class DrezinaTunnelsDB
{
	int Version = 2;
	ref array<ref DrezinaTunnelData> Tunnels = new array<ref DrezinaTunnelData>;
}
