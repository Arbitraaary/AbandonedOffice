#include "SecurityGuardAIController.h"

#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"
#include "UniversityGame/Core/PlayersTeam.h"
#include "UniversityGame/Enemies/SecurityGuard/SecurityGuard.h"
#include "UniversityGame/Environment/Hazards/SmokeZone.h"

ASecurityGuardAIController::ASecurityGuardAIController()
{
	Perception = CreateDefaultSubobject<UAIPerceptionComponent>(TEXT("Perception"));
	Sight = CreateDefaultSubobject<UAISenseConfig_Sight>(TEXT("Sight"));
	Sight->SightRadius = 1800.f;
	Sight->LoseSightRadius = 2300.f;
	Sight->PeripheralVisionAngleDegrees = 70.f;
	Sight->SetMaxAge(4.f);
	Sight->DetectionByAffiliation.bDetectEnemies = true;
	Sight->DetectionByAffiliation.bDetectNeutrals = false;
	Sight->DetectionByAffiliation.bDetectFriendlies = false;
	Perception->ConfigureSense(*Sight);
	Perception->SetDominantSense(Sight->GetSenseImplementation());
	SetPerceptionComponent(*Perception);
}

FGenericTeamId ASecurityGuardAIController::GetGenericTeamId() const
{
	return FGenericTeamId(UniversityTeams::Guards);
}

ETeamAttitude::Type ASecurityGuardAIController::GetTeamAttitudeTowards(const AActor& Other) const
{
	const APawn* OtherPawn = Cast<APawn>(&Other);
	return OtherPawn && OtherPawn->IsPlayerControlled() ? ETeamAttitude::Hostile : ETeamAttitude::Neutral;
}

void ASecurityGuardAIController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	Perception->OnTargetPerceptionUpdated.AddUniqueDynamic(this, &ASecurityGuardAIController::OnTargetPerceived);

	ASecurityGuard* Guard = Cast<ASecurityGuard>(InPawn);
	if (!Guard || !Guard->GetBehaviorTree())
	{
		UE_LOG(LogTemp, Warning, TEXT("%s: no Behavior Tree set on the guard (BP_SecurityGuard -> Behavior Tree)"), *GetName());
		return;
	}
	RunBehaviorTree(Guard->GetBehaviorTree());
	if (UBlackboardComponent* BB = GetBlackboardComponent())
	{
		BB->SetValueAsVector(GuardKeys::PatrolPoint, Guard->PickPatrolLocation());
	}
}

void ASecurityGuardAIController::OnTargetPerceived(AActor* Actor, const FAIStimulus Stimulus)
{
	const APawn* Seen = Cast<APawn>(Actor);
	UBlackboardComponent* BB = GetBlackboardComponent();
	if (!BB || !Seen || !Seen->IsPlayerControlled())
	{
		return;
	}
	if (Stimulus.WasSuccessfullySensed())
	{
		BB->SetValueAsObject(GuardKeys::TargetActor, Actor);
	}
	else
	{
		// lost him: remember where he was last seen and go there
		BB->SetValueAsVector(GuardKeys::LastKnownLocation, Stimulus.StimulusLocation);
		BB->SetValueAsBool(GuardKeys::HasLastKnown, true);
	}
}

bool ASecurityGuardAIController::CanSee(const AActor* Actor) const
{
	if (!Actor || !Perception) return false;
	// smoke blocks the view: the player hiding in it, or the guard standing in it
	if (ASmokeZone::IsActorInSmoke(Actor) || ASmokeZone::IsActorInSmoke(GetPawn())) return false;
	FActorPerceptionBlueprintInfo Info;
	if (!Perception->GetActorsPerception(const_cast<AActor*>(Actor), Info)) return false;
	for (const FAIStimulus& S : Info.LastSensedStimuli)
	{
		if (S.Type == Sight->GetSenseID() && S.WasSuccessfullySensed() && !S.IsExpired())
		{
			return true;
		}
	}
	return false;
}

void ASecurityGuardAIController::ReportThreat(AActor* Threat)
{
	UBlackboardComponent* BB = GetBlackboardComponent();
	if (!BB || !Threat) return;
	BB->SetValueAsObject(GuardKeys::TargetActor, Threat);
	BB->SetValueAsVector(GuardKeys::LastKnownLocation, Threat->GetActorLocation());
	BB->SetValueAsBool(GuardKeys::HasLastKnown, true);
	// turn towards the shooter right away (smoothly - the body follows at the guard's turn rate)
	SetFocalPoint(Threat->GetActorLocation(), EAIFocusPriority::Gameplay);
}
