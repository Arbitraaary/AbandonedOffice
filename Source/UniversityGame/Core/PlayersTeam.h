// Team ids used with IGenericTeamAgentInterface (AI perception "Detect Enemies").

#pragma once

#include "CoreMinimal.h"
#include "GenericTeamAgentInterface.h"

namespace UniversityTeams
{
	constexpr uint8 Players = 0;
	constexpr uint8 Soldiers = 1;
	constexpr uint8 Guards = 2;
}

// the player's team: every AI that is hostile towards PlayersTeam will "see" the player as an enemy
struct FPlayersTeam : public FGenericTeamId
{
	FPlayersTeam() : FGenericTeamId(UniversityTeams::Players) {}
};
