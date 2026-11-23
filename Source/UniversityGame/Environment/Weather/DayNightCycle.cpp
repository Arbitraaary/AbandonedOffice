#include "DayNightCycle.h"

#include "RainWeather.h"
#include "EngineUtils.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "UniversityGame/Environment/Animated/FlickerComponent.h"

ADayNightCycle::ADayNightCycle()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
	Moon->SetupAttachment(RootComponent);
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->SetIntensity(0.f);
	Moon->SetLightColor(FLinearColor(0.55f, 0.65f, 1.f));
	Moon->SetAtmosphereSunLight(false);
	Moon->ForwardShadingPriority = 1;             // the sun (2) is the main light, the moon is next
	Moon->SetCastShadows(true);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	auto MakeDisc = [this](const TCHAR* Name, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* D = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		D->SetupAttachment(RootComponent);
		D->SetStaticMesh(Mesh);
		D->SetAbsolute(true, true, true);
		D->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		D->SetCastShadow(false);
		D->bUseAsOccluder = false;
		D->SetCanEverAffectNavigation(false);
		return D;
	};
	SunDisc = MakeDisc(TEXT("SunDisc"), Sphere.Object);
	MoonDisc = MakeDisc(TEXT("MoonDisc"), Sphere.Object);

	Grading = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Grading"));
	Grading->SetupAttachment(RootComponent);
	Grading->bUnbound = true;
	Grading->Priority = 5.f;
}

void ADayNightCycle::BeginPlay()
{
	Super::BeginPlay();
	FindLevelActors();
	SetupStreetLamps();
	Hour = FMath::Fmod(StartHour, 24.f);
	if (SunMaterial) SunDisc->SetMaterial(0, SunMaterial);
	if (MoonMaterial) MoonDisc->SetMaterial(0, MoonMaterial);
	SetSkyNumber(TEXT("Sun brightness"), 0.f);           // the sky sphere's own sun: our round disc replaces it
	Apply();
}

void ADayNightCycle::FindLevelActors()
{
	UWorld* World = GetWorld();
	if (!Sun)
	{
		for (TActorIterator<ADirectionalLight> It(World); It; ++It)
		{
			Sun = *It;
			break;
		}
	}
	for (TActorIterator<ASkyLight> It(World); It; ++It)
	{
		SkyLight = *It;
		break;
	}
	for (TActorIterator<AExponentialHeightFog> It(World); It; ++It)
	{
		Fog = *It;
		break;
	}
	for (TActorIterator<ARainWeather> It(World); It; ++It)
	{
		Rain = *It;
		break;
	}
	if (!SkySphere)
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (It->GetClass()->GetName().Contains(TEXT("Sky_Sphere")))
			{
				SkySphere = *It;
				break;
			}
		}
	}
	if (Sun)
	{
		if (UDirectionalLightComponent* C = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
		{
			SunIntensity = C->Intensity;
			C->ForwardShadingPriority = 2;          // one main directional light (sun > moon > lightning)
			C->MarkRenderStateDirty();
		}
	}
	if (SkyLight && SkyLight->GetLightComponent())
	{
		SkyIntensity = SkyLight->GetLightComponent()->Intensity;
	}
	if (Fog && Fog->GetComponent())
	{
		FogDensity = Fog->GetComponent()->FogDensity;
		FogColor = Fog->GetComponent()->FogInscatteringLuminance;
	}
}

void ADayNightCycle::SetupStreetLamps()
{
	// a spot light in the head of every lamp; the head is the end of the arm, i.e. the far side of the bounds
	auto AddLamp = [this](AActor* Lamp, const bool bBroken)
	{
		if (!Lamp) return;
		FVector Origin, Extent;
		Lamp->GetActorBounds(false, Origin, Extent);
		const FVector Pole = Lamp->GetActorLocation();
		FVector Head = Pole + (FVector(Origin.X, Origin.Y, Pole.Z) - Pole) * 1.85f;
		Head.Z = Origin.Z + Extent.Z - 25.f;

		USpotLightComponent* L = NewObject<USpotLightComponent>(this);
		L->SetMobility(EComponentMobility::Movable);
		L->SetIntensityUnits(ELightUnits::Candelas);
		L->RegisterComponent();
		L->SetWorldLocationAndRotation(Head, FRotator(-90.f, 0.f, 0.f));
		L->SetIntensity(0.f);
		L->SetAttenuationRadius(bBroken ? 900.f : 1600.f);
		L->SetOuterConeAngle(bBroken ? 40.f : 55.f);
		L->SetInnerConeAngle(20.f);
		L->SetLightColor(bBroken ? FLinearColor(1.f, 0.55f, 0.25f) : FLinearColor(1.f, 0.78f, 0.5f));
		L->SetCastShadows(false);
		L->ComponentTags.Add(bBroken ? FName("Broken") : FName("Working"));
		LampLights.Add(L);
		if (bBroken)
		{
			UFlickerComponent* F = NewObject<UFlickerComponent>(this);
			F->MinCalm = 0.3f;
			F->MaxCalm = 2.f;
			F->DeadChance = 0.5f;
			F->RegisterComponent();
			L->SetIntensity(120.f);             // dim orange; the flicker remembers this as its "on" level
			F->AddLight(L);
		}
	};
	for (AActor* A : StreetLamps) AddLamp(A, false);
	for (AActor* A : BrokenStreetLamps) AddLamp(A, true);
}

void ADayNightCycle::Tick(const float DeltaTime)
{
	Super::Tick(DeltaTime);
	Hour = FMath::Fmod(Hour + DeltaTime * 24.f / FMath::Max(DayLength, 1.f), 24.f);
	Apply();
}

void ADayNightCycle::Apply()
{
	// sun: rises at 6:00 in the east of its path, highest at 12:00, sets at 18:00
	const float Angle = (Hour - 6.f) / 24.f * 360.f;                 // 0 sunrise, 90 noon, 180 sunset
	const float Elevation = FMath::RadiansToDegrees(FMath::Asin(FMath::Sin(FMath::DegreesToRadians(Angle)))) * 0.85f;
	Daylight = FMath::SmoothStep(-6.f, 12.f, Elevation);
	const float RainK = Rain ? Rain->GetStrength() : 0.f;

	if (Sun)
	{
		Sun->SetActorRotation(FRotator(-Angle, SunYaw, 0.f));
		if (ULightComponent* C = Sun->GetLightComponent())
		{
			const float Warm = 1.f - FMath::SmoothStep(2.f, 25.f, Elevation);   // orange near the horizon
			C->SetIntensity(SunIntensity * Daylight * (1.f - 0.75f * RainK));
			C->SetLightColor(FLinearColor::LerpUsingHSV(FLinearColor(1.f, 0.97f, 0.92f), FLinearColor(1.f, 0.55f, 0.28f), Warm));
		}
	}
	// the moon: opposite the sun, only at night
	Moon->SetWorldRotation(FRotator(-FMath::Fmod(Angle + 180.f, 360.f), SunYaw + 160.f, 0.f));
	Moon->SetIntensity(2.5f * (1.f - Daylight) * (1.f - 0.6f * RainK));

	if (SkyLight && SkyLight->GetLightComponent())
	{
		USkyLightComponent* S = SkyLight->GetLightComponent();
		S->SetIntensity(SkyIntensity * (0.75f + 0.25f * Daylight) * (1.f - 0.4f * RainK));   // night: dark blue, not black
		S->SetLightColor(FLinearColor::LerpUsingHSV(NightTint, FLinearColor::White, Daylight));
		const float Now = GetWorld()->GetTimeSeconds();
		if (!S->bRealTimeCapture && Now >= NextSkyRecapture)
		{
			S->RecaptureSky();
			NextSkyRecapture = Now + 2.f;
		}
	}
	if (Fog && Fog->GetComponent())
	{
		UExponentialHeightFogComponent* F = Fog->GetComponent();
		F->SetFogDensity(FogDensity * (1.f + 3.f * RainK));
		const FLinearColor NightFog = NightTint * 0.25f;                 // blue haze at night
		F->SetFogInscatteringColor((FogColor * Daylight + NightFog * (1.f - Daylight)) * (1.f - 0.4f * RainK));
	}

	// exposure: darker at night and in the rain, a little less colour in the rain
	Grading->Settings.bOverride_AutoExposureBias = true;
	Grading->Settings.AutoExposureBias = 0.6f * (1.f - Daylight) - 0.4f * RainK;    // the eye gets used to the night
	// moonlit blue: the picture leans to blue at night
	Grading->Settings.bOverride_ColorGain = true;
	const FLinearColor Gain = FLinearColor::LerpUsingHSV(FLinearColor(0.75f, 0.9f, 1.45f), FLinearColor::White, Daylight);
	Grading->Settings.ColorGain = FVector4(Gain.R, Gain.G, Gain.B, 1.f);
	Grading->Settings.bOverride_ColorSaturation = true;
	Grading->Settings.ColorSaturation = FVector4(1.f, 1.f, 1.f, 1.f - 0.3f * RainK);

	// street lamps: on from dusk to dawn
	const float LampsOn = 1.f - FMath::SmoothStep(0.1f, 0.45f, Daylight);
	for (USpotLightComponent* L : LampLights)
	{
		if (L && L->ComponentHasTag(FName("Working")))
		{
			L->SetIntensity(StreetLampCandelas * LampsOn);
		}
	}

	PlaceDiscs();

	// the sky sphere draws its colours / stars from the light's direction: refresh it now and then
	const float Now = GetWorld()->GetTimeSeconds();
	if (Now >= NextSkyRefresh)
	{
		NextSkyRefresh = Now + 0.1f;
		RefreshSky(0.7f + 0.3f * RainK);
	}
}

void ADayNightCycle::SetSkyNumber(const TCHAR* Name, const float Value, float* OutOld)
{
	// BP_Sky_Sphere variables are float or double depending on the engine version
	if (!SkySphere) return;
	FProperty* P = SkySphere->GetClass()->FindPropertyByName(FName(Name));
	if (FDoubleProperty* D = CastField<FDoubleProperty>(P))
	{
		if (OutOld) *OutOld = static_cast<float>(D->GetPropertyValue_InContainer(SkySphere));
		D->SetPropertyValue_InContainer(SkySphere, Value);
	}
	else if (FFloatProperty* Fl = CastField<FFloatProperty>(P))
	{
		if (OutOld) *OutOld = Fl->GetPropertyValue_InContainer(SkySphere);
		Fl->SetPropertyValue_InContainer(SkySphere, Value);
	}
}

void ADayNightCycle::RefreshSky(const float CloudOpacity)
{
	if (!SkySphere) return;
	// cloud cover (BP_Sky_Sphere variable "Cloud opacity")
	if (SkyCloudOpacity < 0.f)
	{
		float Old = 0.7f;
		SetSkyNumber(TEXT("Cloud opacity"), Old, &Old);      // read it (and write the same value back)
		SkyCloudOpacity = Old;
	}
	SetSkyNumber(TEXT("Cloud opacity"), FMath::Max(SkyCloudOpacity, CloudOpacity));
	for (const TCHAR* Name : {TEXT("UpdateSunDirection"), TEXT("RefreshMaterial")})
	{
		if (UFunction* Fn = SkySphere->FindFunction(FName(Name)))
		{
			if (Fn->ParmsSize == 0)
			{
				SkySphere->ProcessEvent(Fn, nullptr);
			}
		}
	}
}

void ADayNightCycle::PlaceDiscs()
{
	// both discs stay at the same distance from the camera, so they look infinitely far away
	FVector Cam = GetActorLocation();
	if (const APlayerCameraManager* PCM = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		Cam = PCM->GetCameraLocation();
	}
	auto Place = [&](UStaticMeshComponent* Disc, const FVector& Towards, const float Size, const float Visible)
	{
		const bool bShow = Visible > 0.01f && Towards.Z > -0.05f;
		Disc->SetVisibility(bShow);
		if (!bShow) return;
		Disc->SetWorldLocation(Cam + Towards * DiscDistance);
		Disc->SetWorldScale3D(FVector(Size / 100.f));       // the engine sphere is 100 cm across
	};
	const FVector SunDir = Sun ? -Sun->GetActorForwardVector() : FVector::UpVector;   // the light shines from the sun
	const FVector MoonDir = -Moon->GetForwardVector();
	const float RainK = Rain ? Rain->GetStrength() : 0.f;
	Place(SunDisc, SunDir, SunDiscSize, 1.f - RainK);                      // hidden behind the rain clouds
	Place(MoonDisc, MoonDir, MoonDiscSize, (1.f - Daylight) * (1.f - RainK));
}
