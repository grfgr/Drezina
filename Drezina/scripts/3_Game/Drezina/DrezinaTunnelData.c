// Метро: данные тоннеля (tunnels.json). Вся геометрия восстанавливается из A, B и FloorY.
class DrezinaTunnelData
{
	int    Id;
	vector A;        // точка входа A на поверхности (где стоял админ)
	vector B;        // точка входа B
	float  FloorY;   // высота пола тоннеля
	int    TrackId;  // путь (DrezinaTrack) внутри тоннеля
}

class DrezinaTunnelsDB
{
	int Version = 1;
	ref array<ref DrezinaTunnelData> Tunnels = new array<ref DrezinaTunnelData>;
}
