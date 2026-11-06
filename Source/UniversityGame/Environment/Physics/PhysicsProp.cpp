// Base class for props the player can move with physics (loose papers, boxes, bins, cones).

#include "PhysicsProp.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"

APhysicsProp::APhysicsProp()
{
	PrimaryActorTick.bCanEverTick = false;

	StaticMeshComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StaticMesh"));
	RootComponent = StaticMeshComponent;
	StaticMeshComponent->SetMobility(EComponentMobility::Movable);
	StaticMeshComponent->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
	StaticMeshComponent->SetSimulatePhysics(true);
	StaticMeshComponent->SetNotifyRigidBodyCollision(false);
}

void APhysicsProp::BeginPlay()
{
	Super::BeginPlay();

	UPrimitiveComponent* Body = GetPhysicsBody();
	Body->SetMassOverrideInKg(NAME_None, MassKg, true);
	Body->SetLinearDamping(LinearDamping);
	Body->SetAngularDamping(AngularDamping);
	if (!Body->IsSimulatingPhysics())
	{
		UE_LOG(LogTemp, Warning, TEXT("%s: physics is not simulating (mesh %s has no simple collision?)"), *GetName(),
			StaticMeshComponent->GetStaticMesh() ? *StaticMeshComponent->GetStaticMesh()->GetName() : TEXT("none"));
	}
	if (bStartAsleep)
	{
		Body->PutRigidBodyToSleep();
	}
}
