import { zodResolver } from "@hookform/resolvers/zod";
import type { Resolver } from "react-hook-form";
import {
  coerceQuestionnaireValues,
  questionnaireSchema,
  type QuestionnaireFormValues,
} from "@/lib/eworks-calculate-schema";

export const questionnaireResolver: Resolver<QuestionnaireFormValues> = (values, context, options) => {
  return zodResolver(questionnaireSchema)(coerceQuestionnaireValues(values), context, options);
};
