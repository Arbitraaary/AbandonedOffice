#include "LoosePaper.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "GameFramework/Pawn.h"

ALoosePaper::ALoosePaper()
{
	MassKg = 0.05f;
	LinearDamping = 1.8f;     // paper glides, then settles
	AngularDamping = 3.f;

	// thin box = the sheet's physics body; the mesh is only visual
	PaperBody = CreateDefaultSubobject<UBoxComponent>(TEXT("PaperBody"));
	PaperBody->InitBoxExtent(FVector(10.5f, 14.8f, 0.4f));
	PaperBody->SetMobility(EComponentMobility::Movable);
	PaperBody->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
	PaperBody->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);       // characters walk through and trigger it
	PaperBody->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	PaperBody->SetGenerateOverlapEvents(true);
	PaperBody->SetSimulatePhysics(true);
	PaperBody->SetHiddenInGame(true);
	RootComponent = PaperBody;

	StaticMeshComponent->SetupAttachment(PaperBody);
	StaticMeshComponent->SetSimulatePhysics(false);
	StaticMeshComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StaticMeshComponent->SetRelativeLocation(FVector(0.f, 0.f, -0.4f));
}

UPrimitiveComponent* ALoosePaper::GetPhysicsBody() const
{
	return PaperBody;
}

void ALoosePaper::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);

	if (const APawn* Pawn = Cast<APawn>(OtherActor))
	{
		const FVector Velocity = Pawn->GetVelocity();
		if (Velocity.Size2D() > 20.f)
		{
			BlowAway(Velocity, FMath::Clamp(Velocity.Size2D() / 500.f, 0.4f, 1.f));
		}
	}
}

void ALoosePaper::BlowAway(const FVector& WalkerVelocity, const float Strength01)
{
	const float Now = GetWorld()->GetTimeSeconds();
	if (Now - LastBlowTime < Cooldown) return;
	LastBlowTime = Now;

	const float S = FMath::Clamp(Strength01, 0.f, 1.f);
	FVector Dir = WalkerVelocity.GetSafeNormal2D();
	if (Dir.IsNearlyZero())
	{
		Dir = FMath::VRand().GetSafeNormal2D();
	}
	Dir = (Dir + FVector(FMath::FRandRange(-0.6f, 0.6f), FMath::FRandRange(-0.6f, 0.6f), 0.f)).GetSafeNormal2D();

	const FVector Impulse = Dir * FMath::Lerp(MinPush, MaxPush, S)
		+ FVector::UpVector * Lift * S * FMath::FRandRange(0.4f, 1.f);
	PaperBody->WakeRigidBody();
	PaperBody->AddImpulse(Impulse, NAME_None, true);                                  // velocity change
	PaperBody->AddAngularImpulseInDegrees(FMath::VRand() * Spin * S, NAME_None, true);
}
