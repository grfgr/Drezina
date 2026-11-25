// Скриптовая команда персонажа «стою на дрезине».
// Запускается на сервере и у владельца (PlayerBase.CommandHandler), остальным клиентам
// движение реплицируется движком. Каждый кадр ставит игрока на платформу дрезины.
class DrezinaRideCommand extends HumanCommandScript
{
	PlayerBase m_Player;
	Drezina_Handcar m_Handcar;

	void DrezinaRideCommand(PlayerBase player, Drezina_Handcar handcar)
	{
		m_Player = player;
		m_Handcar = handcar;
	}

	bool m_Logged;

	override void OnActivate()
	{
		Print("[Drezina] ride command activated, server=" + GetGame().IsServer());
		// Здесь можно запустить свою анимацию качания рычага, когда появится анимграф (см. README).
	}

	override void OnDeactivate()
	{
		Print("[Drezina] ride command deactivated");
	}

	override void PreAnimUpdate(float pDt)
	{
		// Персонаж стоит в обычной позе. Своё RTM «качание рычага» подключается через анимграф.
	}

	override void PrePhysUpdate(float pDt)
	{
		// гасим собственное перемещение персонажа, позицию задаём в PostPhysUpdate
		PrePhys_SetTranslation(vector.Zero);
	}

	override bool PostPhysUpdate(float pDt)
	{
		if (!m_Handcar || !m_Player || m_Player.m_DrezinaHandcar != m_Handcar || !m_Player.IsAlive())
		{
			SetFlagFinished(true);
			return DrezinaConst.POSTPHYS_CONTINUE;
		}

		vector pos;
		float yaw;
		m_Handcar.GetDriverTransform(pos, yaw);
		if (!m_Logged)
		{
			m_Logged = true;
			Print("[Drezina] ride PostPhys: seat " + pos + ", player " + m_Player.GetPosition());
		}

		vector mat[3];
		Math3D.YawPitchRollMatrix(Vector(yaw, 0, 0), mat);
		float rot[4];
		Math3D.MatrixToQuat(mat, rot);

		PostPhys_SetPosition(pos);
		PostPhys_SetRotation(rot);
		return DrezinaConst.POSTPHYS_CONTINUE;
	}
}
