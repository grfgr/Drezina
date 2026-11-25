// Данные метро для карт других модов (КПК и т.п.). Работает на клиенте: линии и входы
// приходят с сервера (DrezinaRPC.TUNNELS_FULL). Другой мод подключает это через #ifdef DREZINA.
//
//   array<ref array<vector>> lines = new array<ref array<vector>>;
//   array<vector> entrances = new array<vector>;
//   DrezinaMetroMap.Collect(lines, entrances);
//
// lines     — линия каждого тоннеля на поверхности: точки через ~step метров (сглаженный маршрут);
// entrances — входы (головы бункеров) на поверхности, по два на тоннель.
class DrezinaMetroMap
{
	static void Collect(array<ref array<vector>> lines, array<vector> entrances, float step = 20.0)
	{
		DrezinaTunnelManager tm = DrezinaTunnelManager.Get();
		array<ref DrezinaTunnelData> src = tm.m_ClientTunnels;
		// одиночная игра / сервер: берём свои данные
		if (src.Count() == 0 && tm.m_Tunnels.Count() > 0)
		{
			src = new array<ref DrezinaTunnelData>;
			foreach (int id, DrezinaTunnelData td : tm.m_Tunnels)
				src.Insert(td);
		}

		foreach (DrezinaTunnelData t : src)
		{
			if (!t || t.Route.Count() < 2)
				continue;
			DrezinaTrack s = DrezinaTunnelManager.MakeSpline(t.Route, vector.Zero, 0);
			float len = s.GetLength();
			array<vector> pts = new array<vector>;
			float d = 0;
			while (d < len)
			{
				vector p, dir;
				s.GetPosDir(d, p, dir);
				pts.Insert(p);
				d += step;
			}
			vector pe, de;
			s.GetPosDir(len, pe, de);
			pts.Insert(pe);
			lines.Insert(pts);
			entrances.Insert(t.Route[0]);
			entrances.Insert(t.Route[t.Route.Count() - 1]);
		}
	}
}
