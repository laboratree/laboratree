"use client";

/**
 * AnimDirective.kind -> stage component. Mirrors the kinds emitted by the backend lesson
 * scripts (labs/modeling/lessons). Plug IN a stage: add the file under stages/ and list it
 * here; unknown kinds fall back to the family's legacy training animation so a newer backend
 * never blanks the player.
 */

import type { ComponentType } from "react";
import {
  IforestRealStage,
  LofRealStage,
  OcsvmRealStage,
} from "./stages/anomaly-real";
import BoostingAssemblyStage from "./stages/boosting-assembly";
import { DidRealStage, IvRealStage, RctRealStage, RddRealStage } from "./stages/causal-real";
import {
  DbscanRealStage,
  DendrogramRealStage,
  GmmRealStage,
  SpectralRealStage,
} from "./stages/clustering-real";
import ConvSlideStage, { MaxPoolStage } from "./stages/conv-pool";
import DataTableStage from "./stages/data-table";
import LstmGatesStage from "./stages/lstm-gates";
import OptimizerRaceStage from "./stages/optimizer-race";
import HyperparamsStage from "./stages/hyperparams";
import InferenceTableStage from "./stages/inference-table";
import LeafValuesStage from "./stages/leaf-values";
import QuizStage from "./stages/quiz";
import LegacyTestStage from "./stages/legacy-test";
import LegacyTrainStage from "./stages/legacy-train";
import NoteStage from "./stages/note";
import ResidualMorphStage from "./stages/residual-morph";
import RegressionFitStage from "./stages/regression-fit";
import RoadmapStage from "./stages/roadmap";
import RoundTableStage from "./stages/round-table";
import SplitTrialsStage from "./stages/split-trials";
import TreeGrowStage from "./stages/tree-grow";
import type { LessonStageProps } from "./stages/types";
import VerdictStage from "./stages/verdict";
import VolatilityRealStage from "./stages/volatility-real";
import WidgetStage from "./stages/widget";

const STAGES: Record<string, ComponentType<LessonStageProps>> = {
  roadmap: RoadmapStage,
  "data-table": DataTableStage,
  "legacy-train": LegacyTrainStage,
  "legacy-test": LegacyTestStage,
  hyperparams: HyperparamsStage,
  verdict: VerdictStage,
  note: NoteStage,
  widget: WidgetStage,
  "tree-grow": TreeGrowStage,
  "split-trials": SplitTrialsStage,
  "round-table": RoundTableStage,
  "residual-morph": ResidualMorphStage,
  "leaf-values": LeafValuesStage,
  "boosting-assembly": BoostingAssemblyStage,
  quiz: QuizStage,
  "inference-table": InferenceTableStage,
  "conv-slide": ConvSlideStage,
  "max-pool": MaxPoolStage,
  "lstm-gates": LstmGatesStage,
  "optimizer-race": OptimizerRaceStage,
  "dbscan-real": DbscanRealStage,
  "gmm-real": GmmRealStage,
  "dendrogram-real": DendrogramRealStage,
  "spectral-real": SpectralRealStage,
  "iforest-real": IforestRealStage,
  "lof-real": LofRealStage,
  "ocsvm-real": OcsvmRealStage,
  "rct-real": RctRealStage,
  "did-real": DidRealStage,
  "iv-real": IvRealStage,
  "rdd-real": RddRealStage,
  "volatility-real": VolatilityRealStage,
  "regression-fit": RegressionFitStage,
};

export function stageFor(kind: string | undefined): ComponentType<LessonStageProps> {
  return (kind && STAGES[kind]) || LegacyTrainStage;
}

export type { LessonStageProps };
