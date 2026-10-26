(*	----------------------------------------------------------------- 
	 StCd: 3010, 'Umrichter Kommunikationsfehler' 
	 Created by database (WTG8.30)
	 StCd generator: StatuscodeGeneratorEuros_810
	----------------------------------------------------------------- *)
PROGRAM StCd_1002
VAR
	PrevPrgIdx_Ui:				UINT;   (* Bausteinerkennung *)
	FirstRun:					BOOL := TRUE;
	SecondRun:					BOOL := FALSE;
	RepeatTimer:				TONs_retain;
	ResetStatuscodeBo:		BOOL; (* Rücksetzbedingung AutoReset 30 *)
	StCdOperationValid_Bo:	BOOL;
	SetValid_Bo:				BOOL;
	ResetTimer:					TON;
	AutoReset10Bo:				BOOL;
	AutoReset20Bo:				BOOL;
	AutoReset30Bo:				BOOL;
	EvCounterDi:				DINT;
	StCdWithSnap_Bo:			BOOL;
END_VAR
VAR_INPUT
	Idx:							INT;
END_VAR
(* automatisch generierte Variablen *)
VAR
	RebootStCdDelay_TON: TON;
END_VAR
PrevPrgIdx_Ui := PrgIdx_GUi;   (* Bausteinerkennung *)
PrgIdx_GUi := 14097;   (* Bausteinerkennung *)

IF LoadingParams_GBo THEN
	FirstRun := TRUE;
END_IF
IF SecondRun AND RdyForSecondRun_GBo THEN
	ReIdx[Idx] := StCdFindIndexIn(RepeatStCdArUi[Idx], ADR(StCdArUi));
	RepeatTimer(In := (ActRepeatNbArBy[Idx] < MaxRepeatNbArBy[Idx]) AND (ActRepeatNbArBy[Idx] > 0), PTs := RepeatTimeArDw[Idx]);
	SecondRun := FALSE;
END_IF
IF FirstRun AND NOT LoadingParams_GBo THEN
	(* Attribute aus DB *)
	IF (Idx > NbOfStCdCWo) THEN
		DbgErr(CONCAT('Statuscodearray zu kleiner als Idx: ', INT_TO_STRING(Idx)));
		StCdArToSmall_GBo := TRUE;
		PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
		RETURN;
	END_IF
	StCdArUi[Idx] := 1002; (*3010*)
	RepeatStCdArUi[Idx] := 9085; (*455*) 
	MaxRepeatNbArBy[Idx] := 20;
	RepeatTimeArDw[Idx] := 86400;
	TaskCallFrequencyArBy[Idx] := 100;
	OpModeArDw[Idx, 1] := 2#11111111110111111110;
	ZeroLoadOperation_ArBo[Idx] := TRUE;
	AzimutPrgArUs[Idx] := 0;
	HydraulicPrgArUs[Idx] := 0;
	GearOilPumpPrgArUs[Idx] := 0;
	GearHeatingPrgArUs[Idx] := 0;
	GearOilCoolingPrgArUs[Idx] := 0;
	GenFanPrgArUs[Idx] := 0;
	GenHeatingPrgArUs[Idx] := 0;
	VaneAneHeatPrgArUs[Idx] := 0;
	ManResetPrgArUs[Idx] := 0;
	AutoResetPrgArUs[Idx] := 20;
	ResetConverterPrgArUs[Idx] := 0;
	MeanVoltageCBPrgArUs[Idx] := 0;
	GenoLubPrgArUs[Idx] := 0;
	QConverterPrgArUs[Idx] := 20;
	TowerFanPrgArUs[Idx] := 0;
	TrafoPumpPrgArUs[Idx] := 0;
	ConverterMSCPrgArUs[Idx] := 10;
	ConverterGSCPrgArUs[Idx] := 0;
	BrakePrgArUs[Idx] := 20; (*52*)
	RotBearLubPrgArUs[Idx] := 0;
	YawLubPrgArUs[Idx] := 0;
	ZeroLoadPrg_ArBo[Idx] := FALSE;
	StCdWithSnap_Bo := FALSE;
	UserGroupReadArBy[Idx, 0]  := 50;
	UserGroupWriteArBy[Idx, 0] := 50;
	UserGroupReadArBy[Idx, 1]  := 1;
	UserGroupWriteArBy[Idx, 1] := 20;
	UserGroupReadArBy[Idx, 2]  := 1;
	UserGroupWriteArBy[Idx, 2] := 50;
	UserGroupReadArBy[Idx, 3]  := 1;
	UserGroupWriteArBy[Idx, 3] := 20;
	UserGroupReadArBy[Idx, 4]  := 1;
	UserGroupWriteArBy[Idx, 4] := 20;
	UserGroupReadArBy[Idx, 5]  := 1;
	UserGroupWriteArBy[Idx, 5] := 15;
	UserGroupReadArBy[Idx, 6]  := 50;
	UserGroupWriteArBy[Idx, 6] := 50;
	UserGroupReadArBy[Idx, 7]  := 1;
	UserGroupWriteArBy[Idx, 7] := 15;
	UserGroupReadArBy[Idx, 8]  := 1;
	UserGroupWriteArBy[Idx, 8] := 50;
	UserGroupReadArBy[Idx, 9]  := 1;
	UserGroupWriteArBy[Idx, 9] := 50;
	UserGroupReadArBy[Idx, 10]  := 50;
	UserGroupWriteArBy[Idx, 10] := 50;
	UserGroupReadArBy[Idx, 11]  := 50;
	UserGroupWriteArBy[Idx, 11] := 50;
	UserGroupReadArBy[Idx, 12]  := 50;
	UserGroupWriteArBy[Idx, 12] := 50;
	UserGroupReadArBy[Idx, 14]  := 50;
	UserGroupWriteArBy[Idx, 14] := 50;
	UserGroupReadArBy[Idx, 15]  := 50;
	UserGroupWriteArBy[Idx, 15] := 50;
	AlarmArBo[Idx] := TRUE;
	AlarmTypArBy[Idx] := 1;
	AvailabilityGroupArUs[Idx] := 15;
	AvailabilityCalcArBo[Idx] := TRUE;
	FirstRun := FALSE;
	SecondRun := TRUE;
END_IF
(*	-------------------------
	 Initialisierung -> Ende 
	------------------------- *)
IF NOT RdyForWork_GBo THEN
	PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
	RETURN;
END_IF

(*	-----------------
	 Hilfsfunktionen 
	----------------- *)
RebootStCdDelay_TON(IN := TRUE, PT := T#180s);
 
(*	------------------------------
	 Setz- und Rücksetzbedingungen 
	------------------------------ *)
StatusSetArGBo[Idx] := CommFailureConverter_GBo
	AND
	RebootStCdDelay_TON.Q
	AND NOT(StatuscodeActiveArBo[StCd_1045.Idx]);

(*	------------------------------
	 Statuscodeprüfung 
	------------------------------ *)
(* StCdOperationValid_Bo prüft, ob im aktuellen Betriebszustand das Setzten des Statuscodes erlaubt ist *)
StCdOperationValid_Bo := (StCdOperationValidBo(Idx, selectoperationmodeGUd, ADR(OpModeArDw)) OR (ZeroLoadOperation_ArBo[Idx] AND ZeroLoadActive_GBo));
SetValid_Bo := StatusSetArGBo[Idx] AND StCdOperationValid_Bo;

(*	--------------------
	 Wiederholungstimer 
	-------------------- *)
IF RepeatTimer.In THEN
	RepeatTimer();
	IF RepeatTimer.Q THEN
		RepeatTimer(In := FALSE);
		ActRepeatNbArBy[Idx] := 0;
	END_IF
END_IF

(*	---------------------------------------- 
	 Status oder Statuscode inaktiv -> Ende 
	---------------------------------------- *)
IF NOT (StatuscodeActiveArBo[Idx] OR StatusSetArGBo[Idx]) THEN
	PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
	RETURN;
END_IF

(*	-------------------
	 Statuscode zurücksetzen 
	------------------- *)
ResetTimer(PT := T#120000ms);

IF (ResetTimer.Q OR (ResetTimer.PT = T#0ms AND ResetTimer.IN)) AND StatuscodeActiveArBo[Idx] THEN
	StatuscodeActiveArBo[Idx] := FALSE;
	(* Funktionsaufruf im DATACENT *)
	DataCent_ResetStatuscode(
		number := StCdArUi[Idx],
		timestamp := IECTimestamp_GDs,
		manualReset := FALSE,
		accessMode := accessmodeGBy);
END_IF

(*	-------------------
	 Statuscode setzen 
	------------------- *)
IF SetValid_Bo AND NOT StatuscodeActiveArBo[Idx] THEN
	StatuscodeActiveArBo[Idx] := TRUE;
	(* Prüfen ob Anzahl an maximalen Wiederholungen erreicht ist *)
	IF (MaxRepeatNbArBy[Idx] > 0) THEN
		ActRepeatNbArBy[Idx] := ActRepeatNbArBy[Idx] + 1;
	END_IF

	(* Funktionsaufruf im DATACENT *)
	EvCounterDi := DataCent_SetStatuscode(
		number := StCdArUi[Idx],
		timestamp := IECTimestamp_GDs,
		accessMode := accessmodeGBy);

	IF StCdWithSnap_Bo THEN
		IF	NOT SnapActivateDs.SnapActiveBo AND (SnapActivateDs.SnapCodeUd = 0) THEN
			IF AlarmArBo[Idx] THEN
				SfAlarmSnapFileExt_GIn := SnapActFileExtRIn;
			END_IF
			SnapActivateDs.SnapCodeUd			:= StCdArUi[Idx];
			SnapActivateDs.SnapSequNumberIn		:= DINT_TO_INT(EvCounterDi);
			SnapActivateDs.TrigTimestampSt		:= TimeStampMs(ActTime.ActDTMS);
		END_IF
	END_IF


	(* Wiederholungen *)
	IF (ReIdx[Idx] > 0) THEN
		RepeatTimer(In := (ActRepeatNbArBy[Idx] < MaxRepeatNbArBy[Idx]) AND (ActRepeatNbArBy[Idx] > 0));
	END_IF
END_IF

IF (ActRepeatNbArBy[Idx] >= MaxRepeatNbArBy[Idx]) THEN
	StatusSetArGBo[ReIdx[Idx]] := TRUE;
END_IF

(*	-------------------
	 AutoReset 
	------------------- *)
AutoReset10Bo := (AutoResetPrgArUs[Idx] = 10);
AutoReset20Bo := (AutoResetPrgArUs[Idx] = 20) AND NOT StatusSetArGBo[Idx];
AutoReset30Bo := (AutoResetPrgArUs[Idx] = 30) AND ResetStatuscodeBo;

ResetTimer(IN :=
	(AutoReset10Bo OR AutoReset20Bo OR AutoReset30Bo)
	AND StatuscodeActiveArBo[Idx]
	AND CheckBP(BrakePrgArUs[Idx])
	AND (ActRepeatNbArBy[Idx] < MaxRepeatNbArBy[Idx])
	AND NOT ResetTimer.Q)
;

(*	-------------------------------------------
	 Berechnung der Restlaufzeit des Reset Delays 
	------------------------------------------- *)
IF ResetTimer.IN THEN
	ResetTimerRemainingTime_GArTi[Idx] := ResetTimer.PT - ResetTimer.ET;
ELSE
	ResetTimerRemainingTime_GArTi[Idx] := T#0ms;
END_IF

PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
END_PROGRAM