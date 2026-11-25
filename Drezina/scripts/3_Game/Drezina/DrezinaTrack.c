// Данные трассы (то, что хранится в tracks.json) и её геометрия.
// Геометрия строится одинаково на сервере и на клиенте из одних и тех же узлов,
// поэтому клиент может сам плавно двигать дрезину по синхронизированной дистанции.

class DrezinaTrackData
{
	int Id;
	string Name;
	ref array<vector> Nodes = new array<vector>; // точки, поставленные админом
}

class DrezinaTracksDB
{
	int Version = 1;
	ref array<ref DrezinaTrackData> Tracks = new array<ref DrezinaTrackData>;
}

class DrezinaTrack
{
	ref DrezinaTrackData m_Data;

	ref array<vector> m_Points = new array<vector>; // сглаженная линия
	ref array<float>  m_Cum    = new array<float>;  // накопленная длина до точки i
	float m_Length;

	void DrezinaTrack(DrezinaTrackData data)
	{
		m_Data = data;
		Build();
	}

	int GetId()
	{
		return m_Data.Id;
	}

	float GetLength()
	{
		return m_Length;
	}

	// Catmull-Rom через узлы админа, шаг ~SPLINE_STEP.
	void Build()
	{
		m_Points.Clear();
		m_Cum.Clear();
		m_Length = 0;

		array<vector> n = m_Data.Nodes;
		int count = n.Count();
		if (count == 0)
			return;

		if (count == 1)
		{
			m_Points.Insert(n[0]);
			m_Cum.Insert(0);
			return;
		}

		m_Points.Insert(n[0]);
		for (int i = 0; i < count - 1; i++)
		{
			vector p0 = n[Math.Max(i - 1, 0)];
			vector p1 = n[i];
			vector p2 = n[i + 1];
			vector p3 = n[Math.Min(i + 2, count - 1)];

			float segLen = vector.Distance(p1, p2);
			int steps = Math.Ceil(segLen / DrezinaConst.SPLINE_STEP);
			if (steps < 1)
				steps = 1;
			for (int s = 1; s <= steps; s++)
			{
				float t = s;
				t = t / steps; // без этого было бы целочисленное деление
				m_Points.Insert(CatmullRom(p0, p1, p2, p3, t));
			}
		}

		m_Cum.Insert(0);
		for (int k = 1; k < m_Points.Count(); k++)
		{
			m_Length += vector.Distance(m_Points[k - 1], m_Points[k]);
			m_Cum.Insert(m_Length);
		}
	}

	static vector CatmullRom(vector p0, vector p1, vector p2, vector p3, float t)
	{
		float t2 = t * t;
		float t3 = t2 * t;
		vector r = (p1 * 2.0) + (p2 - p0) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2 + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3;
		return r * 0.5;
	}

	// Позиция и направление (вдоль роста дистанции) в точке d.
	void GetPosDir(float d, out vector pos, out vector dir)
	{
		int cnt = m_Points.Count();
		if (cnt == 0)
		{
			pos = vector.Zero;
			dir = "0 0 1";
			return;
		}
		if (cnt == 1)
		{
			pos = m_Points[0];
			dir = "0 0 1";
			return;
		}

		d = Math.Clamp(d, 0, m_Length);

		// бинарный поиск отрезка
		int lo = 0;
		int hi = cnt - 1;
		while (hi - lo > 1)
		{
			int mid = (lo + hi) / 2;
			if (m_Cum[mid] <= d)
				lo = mid;
			else
				hi = mid;
		}

		float segLen = m_Cum[hi] - m_Cum[lo];
		float f = 0;
		if (segLen > 0.0001)
			f = (d - m_Cum[lo]) / segLen;

		pos = m_Points[lo] + (m_Points[hi] - m_Points[lo]) * f;
		dir = vector.Direction(m_Points[lo], m_Points[hi]).Normalized();
	}

	// Ближайшая к точке дистанция по пути и расстояние до неё.
	float ClosestDistance(vector p, out float outDist)
	{
		float best = 1000000000.0;
		float bestD = 0;
		for (int i = 0; i < m_Points.Count(); i++)
		{
			float dd = vector.DistanceSq(p, m_Points[i]);
			if (dd < best)
			{
				best = dd;
				bestD = m_Cum[i];
			}
		}
		outDist = Math.Sqrt(best);
		return bestD;
	}

	// Сериализация для RPC (узлов достаточно, геометрия строится на клиенте).
	static void Write(ParamsWriteContext ctx, DrezinaTrackData data)
	{
		ctx.Write(data.Id);
		ctx.Write(data.Name);
		int c = data.Nodes.Count();
		ctx.Write(c);
		for (int i = 0; i < c; i++)
			ctx.Write(data.Nodes[i]);
	}

	static DrezinaTrackData Read(ParamsReadContext ctx)
	{
		DrezinaTrackData data = new DrezinaTrackData();
		if (!ctx.Read(data.Id))
			return null;
		if (!ctx.Read(data.Name))
			return null;
		int c;
		if (!ctx.Read(c))
			return null;
		for (int i = 0; i < c; i++)
		{
			vector v;
			if (!ctx.Read(v))
				return null;
			data.Nodes.Insert(v);
		}
		return data;
	}
}
