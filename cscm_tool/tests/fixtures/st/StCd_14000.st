(*	----------------------------------------------------------------- 
	 StCd: 14000, 'Rotorüberdrehzahl' 
	 Created by database (Arbeitsversion)
	 StCd generator: StatuscodeGeneratorEuros_810
	----------------------------------------------------------------- *)
PROGRAM StCd_14000
VAR
	PrevPrgIdx_Ui:				UINT;   (* Bausteinerkennung *)
	FirstRun:					BOOL := TRUE;
	ResetStatuscodeBo:		BOOL; (* Rücksetzbedingung AutoReset 30 *)
	StCdOperationValid_Bo:	BOOL;
	SetTimer:					TON;
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
PrevPrgIdx_Ui := PrgIdx_GUi;   (* Bausteinerkennung *)
PrgIdx_GUi := 18926;   (* Bausteinerkennung *)

IF LoadingParams_GBo THEN
	FirstRun := TRUE;
END_IF
IF FirstRun AND NOT LoadingParams_GBo THEN
	(* Attribute aus DB *)
	IF (Idx > NbOfStCdCWo) THEN
		DbgErr(CONCAT('Statuscodearray zu kleiner als Idx: ', INT_TO_STRING(Idx)));
		StCdArToSmall_GBo := TRUE;
		PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
		RETURN;
	END_IF
	StCdArUi[Idx] := 14000;
	TaskCallFrequencyArBy[Idx] := 1;
	OpModeArDw[Idx, 1] := 2#111011;
	ManResetPrgArUs[Idx] := 0;
	AutoResetPrgArUs[Idx] := 30;
	BrakePrgArUs[Idx] := 80;
	PtErrOpPrgArUs[Idx] := 0;
	PtWarnOpPrgArUs[Idx] := 0;
	RotorBrakePrgArUs[Idx] := 20;
	StCdWithSnap_Bo := TRUE;
	UserGroupReadArBy[Idx, 0]  := 50;
	UserGroupWriteArBy[Idx, 0] := 50;
	UserGroupReadArBy[Idx, 1]  := 1;
	UserGroupWriteArBy[Idx, 1] := 50;
	UserGroupReadArBy[Idx, 2]  := 1;
	UserGroupWriteArBy[Idx, 2] := 50;
	UserGroupReadArBy[Idx, 3]  := 1;
	UserGroupWriteArBy[Idx, 3] := 50;
	UserGroupReadArBy[Idx, 4]  := 1;
	UserGroupWriteArBy[Idx, 4] := 50;
	UserGroupReadArBy[Idx, 5]  := 50;
	UserGroupWriteArBy[Idx, 5] := 50;
	UserGroupReadArBy[Idx, 6]  := 50;
	UserGroupWriteArBy[Idx, 6] := 50;
	UserGroupReadArBy[Idx, 7]  := 50;
	UserGroupWriteArBy[Idx, 7] := 50;
	UserGroupReadArBy[Idx, 8]  := 1;
	UserGroupWriteArBy[Idx, 8] := 50;
	UserGroupReadArBy[Idx, 9]  := 50;
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
	AlarmArBo[Idx] := FALSE;
	AlarmTypArBy[Idx] := 1;
	AvailabilityGroupArUs[Idx] := 7;
	AvailabilityCalcArBo[Idx] := FALSE;
	FirstRun := FALSE;
END_IF
(*	-------------------------
	 Initialisierung -> Ende 
	------------------------- *)
IF NOT RdyForWork_GBo THEN
	PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
	RETURN;
END_IF

 
(*	------------------------------
	 Setz- und Rücksetzbedingungen 
	------------------------------ *)
StatusSetArGBo[Idx] := iv10msRotRpmRepHcFast_GRe > RotRpmMonLim_GRe;

(*	--------------
	 Autoreset 30 
	-------------- *)
ResetStatuscodeBo := iv10msRotRpmRepHcFast_GRe < 2.0;

(*	------------------------------
	 Statuscodeprüfung 
	------------------------------ *)
(* StCdOperationValid_Bo prüft, ob im aktuellen Betriebszustand das Setzten des Statuscodes erlaubt ist *)
StCdOperationValid_Bo := StCdOperationValidBo(Idx, selectoperationmodeGUd, ADR(OpModeArDw));
SetTimer(PT := StCd14000SetDelayGpTi, IN := StatusSetArGBo[Idx] AND StCdOperationValid_Bo);

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
ResetTimer(PT := T#200ms);

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
IF (SetTimer.Q OR (SetTimer.PT = T#0ms AND SetTimer.IN)) AND NOT StatuscodeActiveArBo[Idx] THEN
	StatuscodeActiveArBo[Idx] := TRUE;

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