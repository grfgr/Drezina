// Объекты метро. Все спавнятся сервером из tunnels.json и в CE-хранилище не пишутся.

// Голова бункера с гермодверью на поверхности (модель bunker_entrance).
class Drezina_MetroHatch extends House
{
	int m_TunnelId; // только сервер
	int m_End;      // 0 = вход A, 1 = вход B
}

// Гермодверь изнутри, на верхней площадке лестницы (модель bunker_inner_door).
class Drezina_MetroLadder extends House
{
	int m_TunnelId;
	int m_End;
}

class Drezina_Tunnel10 extends House {}
class Drezina_Tunnel2 extends House {}
class Drezina_MetroStation extends House {}
class Drezina_Rail10 extends House {}
class Drezina_BunkerStairs extends House {}
class Drezina_BunkerCorridor extends House {}
