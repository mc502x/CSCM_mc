(*	----------------------------------------------------------------- 
	 StCd: 14005, 'Test Rotorüberdrehzahl' 
	 Created by database (Arbeitsversion)
	 StCd generator: StatuscodeGeneratorEuros_810
	----------------------------------------------------------------- *)
PROGRAM StCd_14005
VAR
	PrevPrgIdx_Ui:				UINT;   (* Bausteinerkennung *)
	FirstRun:					BOOL := TRUE;
	ResetStatuscodeBo:		BOOL; (* Rücksetzbedingung AutoReset 30 *)
	StCdOperationValid_Bo:	BOOL;
	SetValid_Bo:				BOOL;
	ResetValid_Bo:				BOOL;
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

PrevPrgIdx_Ui := PrgIdx_GUi;   (* Bausteinerkennung *)
PrgIdx_GUi := 18931;   (* Bausteinerkennung *)

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
	StCdArUi[Idx] := 14005;
	TaskCallFrequencyArBy[Idx] := 1;
	OpModeArDw[Idx, 1] := 2#111011;
	ManResetPrgArUs[Idx] := 0;
	AutoResetPrgArUs[Idx] := 20;
	BrakePrgArUs[Idx] := 0;
	PtErrOpPrgArUs[Idx] := 0;
	PtWarnOpPrgArUs[Idx] := 0;
	RotorBrakePrgArUs[Idx] := 0;
	StCdWithSnap_Bo := FALSE;
	UserGroupReadArBy[Idx, 0]  := 50;
	UserGroupWriteArBy[Idx, 0] := 50;
	UserGroupReadArBy[Idx, 1]  := 1;
	UserGroupWriteArBy[Idx, 1] := 20;
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
	AlarmTypArBy[Idx] := 3;
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
StatusSetArGBo[Idx] := VisReqHcRotRpmMonTest_GsBo AND VisReqHcSemiAutoHcActivate_GsBo;

(*	------------------------------
	 Statuscodeprüfung 
	------------------------------ *)
(* StCdOperationValid_Bo prüft, ob im aktuellen Betriebszustand das Setzten des Statuscodes erlaubt ist *)
StCdOperationValid_Bo := StCdOperationValidBo(Idx, selectoperationmodeGUd, ADR(OpModeArDw));
SetValid_Bo := StatusSetArGBo[Idx] AND StCdOperationValid_Bo;

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
IF ResetValid_Bo AND StatuscodeActiveArBo[Idx] THEN
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

ResetValid_Bo :=
	(AutoReset10Bo OR AutoReset20Bo OR AutoReset30Bo)
	AND StatuscodeActiveArBo[Idx]
	AND CheckBP(BrakePrgArUs[Idx])
;

PrgIdx_GUi := PrevPrgIdx_Ui;   (* Bausteinerkennung *)
END_PROGRAM