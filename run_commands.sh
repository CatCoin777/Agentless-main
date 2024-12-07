#Localization
mkdir results # where we will save our results
python agentless/fl/localize.py --file_level --related_level --fine_grain_line_level \
                                --output_folder results/location --top_n 3 \
                                --compress \
                                --context_window=10 \
                                --temperature 0.8 \
                                --num_samples 4 \
                                --model /gemini/platform/public/llm/huggingface/Qwen/Qwen2.5-Coder-32B-Instruct \
                                --input_data output_7b.json

#合并
python agentless/fl/localize.py --merge \
                                --output_folder results/location_merged \
                                --start_file results/location/loc_outputs.jsonl \
                                --num_samples 4 \
                                --model /gemini/platform/public/llm/huggingface/Qwen/Qwen2.5-Coder-32B-Instruct \
                                --input_data output_7b.json
#repair
python agentless/repair/repair.py --loc_file results/location_merged/loc_merged_0-1_outputs.jsonl \
                                  --output_folder results/repair_run_1 \
                                  --loc_interval --top_n=3 --context_window=10 \
                                  --max_samples 21  --cot --diff_format \
                                  --gen_and_process \
                                  --model /gemini/platform/public/llm/huggingface/Qwen/Qwen2.5-Coder-32B-Instruct\
                                  --input_data output_7b.json
python agentless/repair/repair.py --loc_file results/location_merged/loc_merged_2-3_outputs.jsonl \
                                  --output_folder results/repair_run_2 \
                                  --loc_interval --top_n=3 --context_window=10 \
                                  --max_samples 21  --cot --diff_format \
                                  --gen_and_process \
                                  --model /gemini/platform/public/llm/huggingface/Qwen/Qwen2.5-Coder-32B-Instruct \
                                  --input_data output_7b.json

python agentless/repair/rerank.py --patch_folder results/repair_run_1,results/repair_run_2 --num_samples 42 --deduplicate --plausible
