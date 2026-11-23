// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BaseWeapon.generated.h"

class UBoxComponent;
class UStaticMesh;
class UStaticMeshComponent;
class ABullet;

UCLASS()
class UNIVERSITYGAME_API ABaseWeapon : public AActor
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	ABaseWeapon();
	
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Mesh")
	USkeletalMeshComponent* SkeletalMeshComponent ;
	
protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Properties")
	bool bInfiniteAmmo = false;
	
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	int GeneralAmmoCapacity = 120;

	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	int MagazineAmmoCapacity = 30;
	
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	int UnequippedAmmoCount = 120;

	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	int MagazineAmmoCount = 30;

	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	float FireRate = 0.1f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Projectiles")
	TSubclassOf<ABullet> BulletClass;

	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	FName Socket;

	// socket at the end of the barrel where bullets appear; if empty or missing on the mesh,
	// "b_gun_muzzle_flash_socket" is used as before (the guard's AR4 uses "Muzzle")
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Properties")
	FName MuzzleSocketName;
	
	// RELOAD VISUALS BEGIN
	// magazine model held in the hand during the reload; if empty it is found next to the weapon mesh
	// (SK_KA47_X -> SM_KA47_Mag, SK_KA74U_X -> SM_KA74U_Mag_X ...)
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Reload")
	UStaticMesh* MagazineMesh = nullptr;

	// the magazine bone of the weapon mesh (hidden while the magazine is in the hand)
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Reload")
	FName MagazineBoneName = TEXT("b_gun_mag");

	// the hand bone the magazine follows
	UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Reload")
	FName MagazineHandBone = TEXT("hand_l");

	UPROPERTY()
	UStaticMeshComponent* HandMagazine = nullptr;

	UStaticMesh* FindMagazineMesh();
	// RELOAD VISUALS END

	bool bCanFire = true;

	FTimerHandle FireRateTimerHandle;

public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

	TSubclassOf<ABullet> GetBulletClass() const;

	FVector GetMuzzleLocation() const;
	
	FVector GetSightLocation() const;

	float GetFireRate() const;

	void Fire(const FRotator& BulletInitialRotation, const FVector& BulletLaunchDirection);

	bool ReadyToFire() const;
	
	bool IsMagEmpty() const;

	void ResetFireCooldown();

	FVector GetWeaponDirection() const;

	bool CanReload() const;

	void Reload();

	// one reload step: moves up to MaxRounds from the reserve into the magazine, returns how many were moved
	int ReloadRounds(int MaxRounds);

	// reload animation: the hand pulls the magazine out (it leaves the weapon and follows the hand) ...
	void MagazineOut(USkeletalMeshComponent* HandMesh);

	// ... and puts it back in (also called when the reload ends or is interrupted)
	void MagazineIn();

	void SetInfiniteAmmo(bool IsInfinite);

	bool GetInfiniteAmmo() const;

	int GetGeneralAmmoCapacity() const;
	int GetMagazineAmmoCapacity() const;
	int GetUnequippedAmmoCount() const;
	int GetMagazineAmmoCount() const;

	void CopyFrom(const ABaseWeapon* OtherWeapon);

	void AddAmmo(int AmmoCount);

	FName GetSocketName() const;
};
