#include "GrabbableProp.h"

#include "Components/StaticMeshComponent.h"

AGrabbableProp::AGrabbableProp()
{
	MassKg = 4.f;
	LinearDamping = 0.2f;
	AngularDamping = 0.5f;
}

void AGrabbableProp::OnGrabbed()
{
	bHeld = true;
	// while carried it must not push the player who holds it
	StaticMeshComponent->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	StaticMeshComponent->WakeRigidBody();
}

void AGrabbableProp::OnReleased()
{
	bHeld = false;
	StaticMeshComponent->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	StaticMeshComponent->WakeRigidBody();
}
