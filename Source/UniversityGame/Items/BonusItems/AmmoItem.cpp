// Fill out your copyright notice in the Description page of Project Settings.


#include "AmmoItem.h"

#include "Components/SphereComponent.h"
#include "Kismet/KismetMathLibrary.h"
#include "UniversityGame/Character/MainCharacter.h"

// Sets default values
AAmmoItem::AAmmoItem()
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
void AAmmoItem::BeginPlay()
{
	Super::BeginPlay();
	
}

// Called every frame
void AAmmoItem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	SphereComponent->AddRelativeRotation(FRotator(0.0f, ItemRotationSpeed, 0.0f));
	SphereComponent->AddRelativeLocation(FVector(0.0f, 0.0f, UKismetMathLibrary::Sin(CurrentAscendingRadianValue + DeltaTime) * ItemMaxAscendingHeight));
	CurrentAscendingRadianValue += ItemAscendingSpeed;
}

void AAmmoItem::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);

	if (AMainCharacter* Player = Cast<AMainCharacter>(OtherActor); Player != nullptr)
	{
		const int Added = Player->GetAmmo(FMath::RoundToInt(AdditionalAmmoAmount));
		if (Added > 0)
		{
			Player->ShowPickupMessage(FText::FromString(FString::Printf(TEXT("+%d AMMO"), Added)),
				FLinearColor(1.f, 0.85f, 0.3f));
			Destroy();
		}
		else
		{
			// reserve already full: the crate stays where it is, so it isn't wasted
			Player->ShowPickupMessage(FText::FromString(TEXT("AMMO IS FULL")), FLinearColor(0.75f, 0.75f, 0.75f), 1.5f);
		}
	}
}
