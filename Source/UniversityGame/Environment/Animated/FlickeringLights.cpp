#include "FlickeringLights.h"

#include "FlickerComponent.h"
#include "Components/BillboardComponent.h"
#include "Components/LightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AFlickeringLights::AFlickeringLights()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
#if WITH_EDITORONLY_DATA
	if (UBillboardComponent* Icon = CreateEditorOnlyDefaultSubobject<UBillboardComponent>(TEXT("Icon")))
	{
		Icon->SetupAttachment(RootComponent);
	}
#endif
}

void AFlickeringLights::BeginPlay()
{
	Super::BeginPlay();
	for (AActor* Target : Targets)
	{
		if (!Target) continue;
		UFlickerComponent* Flicker = NewObject<UFlickerComponent>(this);
		Flicker->MinCalm = MinCalm;
		Flicker->MaxCalm = MaxCalm;
		Flicker->RegisterComponent();

		TArray<ULightComponent*> Lights;
		Target->GetComponents<ULightComponent>(Lights);
		for (ULightComponent* Light : Lights)
		{
			Flicker->AddLight(Light);
		}

		TArray<UStaticMeshComponent*> Meshes;
		Target->GetComponents<UStaticMeshComponent>(Meshes);
		for (UStaticMeshComponent* Mesh : Meshes)
		{
			for (int32 i = 0; i < Mesh->GetNumMaterials(); ++i)
			{
				float Value = 0.f;
				const UMaterialInterface* Material = Mesh->GetMaterial(i);
				if (Material && Material->GetScalarParameterValue(FHashedMaterialParameterInfo(EmissiveParameter), Value))
				{
					Flicker->AddMaterial(Mesh->CreateDynamicMaterialInstance(i), EmissiveParameter);
				}
			}
		}
	}
}
