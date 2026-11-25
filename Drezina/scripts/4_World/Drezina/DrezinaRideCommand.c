// Скриптовая команда персонажа «стою на дрезине».
// Запускается на сервере и у владельца (PlayerBase.CommandHandler), остальным клиентам
// движение реплицируется движком. Каждый кадр ведёт игрока за платформой дрезины:
//  - PrePhys: смещение к сиденью через физику персонажа (в локальных осях персонажа);
//  - PostPhys: точная установка позиции и поворота (в мировых осях);
//  - гравитация на время езды выключена, чтобы персонаж не «сползал» с движущейся платформы.
class DrezinaRideCommand extends HumanCommandScript
{
	PlayerBase m_Player;
	Drezina_Handcar m_Handcar;
	float m_LogTimer;

	void DrezinaRideCommand(PlayerBase player, Drezina_Handcar handcar)
	{
		m_Player = player;
		m_Handcar = handcar;
	}

	override void OnActivate()
	{
		Print("[Drezina] ride command activated, server=" + GetGame().IsServer());
		if (m_Player)
			m_Player.PhysicsEnableGravity(false);
		if (m_Handcar)
			m_Handcar.m_TickedByRide = true;
	}

	override void OnDeactivate()
	{
		Print("[Drezina] ride command deactivated");
		if (m_Player)
			m_Player.PhysicsEnableGravity(true);
		if (m_Handcar)
			m_Handcar.m_TickedByRide = false;
	}

	override void PreAnimUpdate(float pDt)
	{
		// Персонаж стоит в обычной позе. Своё RTM «качание рычага» подключается через анимграф.
	}

	bool Valid()
	{
		return m_Handcar && m_Player && m_Player.m_DrezinaHandcar == m_Handcar && m_Player.IsAlive();
	}

	override void PrePhysUpdate(float pDt)
	{
		if (!Valid())
		{
			PrePhys_SetTranslation(vector.Zero);
			return;
		}
		// сначала сдвинуть дрезину на этот кадр, потом вести за ней персонажа — в одной фазе
		m_Handcar.Tick(pDt);
		vector seat;
		float yaw;
		m_Handcar.GetDriverTransform(seat, yaw);
		// весь путь до сиденья за этот кадр, в локальных осях персонажа
		vector delta = seat - m_Player.GetPosition();
		PrePhys_SetTranslation(m_Player.VectorToLocal(delta));
	}

	override bool PostPhysUpdate(float pDt)
	{
		if (!Valid())
		{
			SetFlagFinished(true);
			return DrezinaConst.POSTPHYS_CONTINUE;
		}

		vector seat;
		float yaw;
		m_Handcar.GetDriverTransform(seat, yaw);

		m_LogTimer -= pDt;
		if (m_LogTimer <= 0)
		{
			m_LogTimer = 1.0;
			vector got;
			PostPhys_GetPosition(got);
			Print("[Drezina] ride server=" + GetGame().IsServer() + " seat " + seat + " phys " + got + " off " + vector.Distance(got, seat));
		}

		vector mat[3];
		Math3D.YawPitchRollMatrix(Vector(yaw, 0, 0), mat);
		float rot[4];
		Math3D.MatrixToQuat(mat, rot);

		PostPhys_SetPosition(seat);
		PostPhys_SetRotation(rot);
		return DrezinaConst.POSTPHYS_CONTINUE;
	}
}
