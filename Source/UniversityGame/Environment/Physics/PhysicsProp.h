// Base class for props the player can move with physics (loose papers, boxes, bins, cones).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PhysicsProp.generated.h"

UCLASS(Abstract)
class UNIVERSITYGAME_API APhysicsProp : public AActor
{
	GENERATED_BODY()

public:
	APhysicsProp();

	UStaticMeshComponent* GetMesh() const { return StaticMeshComponent; }

	// the component that simulates (the mesh itself, or a simple collision body the mesh is attached to)
	virtual UPrimitiveComponent* GetPhysicsBody() const { return StaticMeshComponent; }

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = Mesh)
	UStaticMeshComponent* StaticMeshComponent;

	// mass used by the physics simulation (the mesh's own mass is ignored)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics, meta = (ClampMin = "0.01"))
	float MassKg = 2.f;

	// "air resistance" while sliding / flying
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float LinearDamping = 0.1f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	float AngularDamping = 0.2f;

	// props start asleep: stacks of boxes / piles of papers stay put until something touches them
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = Physics)
	bool bStartAsleep = true;
};
