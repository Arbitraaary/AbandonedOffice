// Fill out your copyright notice in the Description page of Project Settings.


#include "HealthItem.h"

#include "Components/SphereComponent.h"
#include "Kismet/KismetMathLibrary.h"
#include "UniversityGame/Character/MainCharacter.h"

// Sets default values
AHealthItem::AHealthItem()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

	if (SphereComponent == nullptr)
	{
		SphereComponent = CreateDefaultSubobject<USphereComponent>(TEXT("SphereComponent"));
		SphereComponent->InitSphereRadius(30.f);
		SphereComponent->SetRelativeRotation(FRotator(0.0f, 0.0f, 0.0f));
		RootComponent = SphereComponent;
	}

	// Mesh
	StaticMeshComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StaticMesh"));
	StaticMeshComponent->SetupAttachment(SphereComponent);

	SphereComponent->BodyInstance.SetCollisionProfileName(TEXT("BonusItem"));
}

// Called when the game starts or when spawned
void AHealthItem::BeginPlay()
{
	Super::BeginPlay();
	
}

// Called every frame
void AHealthItem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	SphereComponent->AddRelativeRotation(FRotator(0.0f, ItemRotationSpeed, 0.0f));
	SphereComponent->AddRelativeLocation(FVector(0.0f, 0.0f, UKismetMathLibrary::Sin(CurrentAscendingRadianValue + DeltaTime) * ItemMaxAscendingHeight));
	CurrentAscendingRadianValue += ItemAscendingSpeed;
}

void AHealthItem::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);

	if (AMainCharacter* Player = Cast<AMainCharacter>(OtherActor); Player != nullptr)
	{
		const float Healed = Player->Heal(HealthRecoveryAmount);
		if (Healed > 0.f)
		{
			Player->ShowPickupMessage(FText::FromString(FString::Printf(TEXT("+%d HEALTH"), FMath::RoundToInt(Healed))),
				FLinearColor(0.35f, 1.f, 0.4f));
			Destroy();
		}
		else
		{
			// health already full: the medkit stays where it is
			Player->ShowPickupMessage(FText::FromString(TEXT("HEALTH IS FULL")), FLinearColor(0.75f, 0.75f, 0.75f), 1.5f);
		}
	}
}
