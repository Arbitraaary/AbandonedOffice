#include "HangingLamp.h"

#include "FlickerComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/PointLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"

AHangingLamp::AHangingLamp()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;   // light follows even off-screen

	// the model and its swing from Blender (imported by setup_lab6_scene.py)
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> LampMesh(
		TEXT("/Game/_Game/Environment/AbandonedOffice/Animated/HangingLamp/SK_FluorescentLamp.SK_FluorescentLamp"));
	if (LampMesh.Succeeded())
	{
		Mesh->SetSkeletalMeshAsset(LampMesh.Object);
	}
	static ConstructorHelpers::FObjectFinder<UAnimSequence> Swing(
		TEXT("/Game/_Game/Environment/AbandonedOffice/Animated/HangingLamp/A_FluorescentLamp_Swing.A_FluorescentLamp_Swing"));
	if (Swing.Succeeded())
	{
		SwingAnimation = Swing.Object;
	}

	TubeLight = CreateDefaultSubobject<URectLightComponent>(TEXT("TubeLight"));
	TubeLight->SetupAttachment(Mesh, TEXT("light"));             // the bone points out of the open side
	TubeLight->SetMobility(EComponentMobility::Movable);
	TubeLight->SetIntensity(25.f);
	TubeLight->SetLightColor(FLinearColor(0.85f, 0.92f, 1.f));
	TubeLight->SetSourceWidth(14.f);
	TubeLight->SetSourceHeight(90.f);
	TubeLight->SetAttenuationRadius(900.f);
	TubeLight->SetBarnDoorAngle(70.f);
	TubeLight->SetCastShadows(true);

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Mesh, TEXT("light"));
	Glow->SetMobility(EComponentMobility::Movable);
	Glow->SetIntensity(400.f);
	Glow->SetLightColor(FLinearColor(0.85f, 0.92f, 1.f));
	Glow->SetAttenuationRadius(350.f);
	Glow->SetCastShadows(false);

	Flicker = CreateDefaultSubobject<UFlickerComponent>(TEXT("Flicker"));
	Flicker->MinCalm = 2.5f;
	Flicker->MaxCalm = 8.f;
}

void AHangingLamp::BeginPlay()
{
	Super::BeginPlay();
	if (SwingAnimation)
	{
		Mesh->PlayAnimation(SwingAnimation, true);
		Mesh->SetPlayRate(SwingPlayRate);
		Mesh->SetPosition(FMath::FRandRange(0.f, SwingAnimation->GetPlayLength()), false);   // not every lamp in step
	}
	// one line in the log a second after start: where the lamp really is (checks the import scale)
	FTimerHandle Check;
	GetWorldTimerManager().SetTimer(Check, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		const FVector Top = GetActorLocation();
		const FVector LampEnd = Mesh->DoesSocketExist(TEXT("dangle_02")) ? Mesh->GetSocketLocation(TEXT("dangle_02")) : Top;
		UE_LOG(LogTemp, Display, TEXT("[Lab6Lamp] %s mesh=%s anim=%s visible=%d lowest bone %.0f cm below the anchor, bounds %s"),
		       *GetName(), *GetNameSafe(Mesh->GetSkeletalMeshAsset()), *GetNameSafe(SwingAnimation), Mesh->IsVisible(),
		       Top.Z - LampEnd.Z, *Mesh->Bounds.BoxExtent.ToString());
	}), 1.f, false);

	Flicker->AddLight(TubeLight);
	Flicker->AddLight(Glow);
	if (TubeMaterialIndex < Mesh->GetNumMaterials())
	{
		Flicker->AddMaterial(Mesh->CreateDynamicMaterialInstance(TubeMaterialIndex), TubeGlowParameter);
	}
}
