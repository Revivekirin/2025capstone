import pandas as pd
import os
import glob

def merge_and_update_shodan_csv(directory_path):
    """
    지정된 디렉토리 내 모든 CSV 파일을 기준 파일(shodan_data.csv)과 병합하고,
    기준 파일에는 없는 새로운 행만 추가하여 저장합니다.
    병합할 파일들에서 누락된 컬럼은 NaN으로 채웁니다.
    병합 완료 후 원본 CSV 파일들은 삭제됩니다.
    
    URL 기준으로 중복된 경우 기존(shodan_data.csv)의 행을 보존하고,
    새로운 중복된 행은 제거합니다.

    Args:
        directory_path (str): 대상 CSV 파일들이 있는 디렉토리 경로
    """
    print(f"작업 시작: {directory_path} 디렉토리 처리 중...")

    # 1. 디렉토리 유효성 확인
    target_path = os.path.expanduser(directory_path)
    if not os.path.isdir(target_path):
        print(f"오류: 디렉토리가 존재하지 않습니다 - {target_path}")
        return

    # 2. 병합 대상 파일 리스트 가져오기
    output_filename = "shodan_data.csv"
    output_filepath = os.path.join(target_path, output_filename)

    # output_filepath을 제외한 모든 CSV 파일 검색
    csv_files_to_merge = [
        f for f in glob.glob(os.path.join(target_path, "*.csv"))
        if os.path.abspath(f) != os.path.abspath(output_filepath)
    ]

    if not csv_files_to_merge and not os.path.exists(output_filepath):
        print(f"정보: 병합할 CSV 파일도 없고, 기준 파일({output_filename})도 없습니다. 작업을 종료합니다.")
        return
    elif not csv_files_to_merge:
        print(f"정보: 병합할 새로운 CSV 파일이 없습니다. 기준 파일({output_filename})만 존재합니다. 작업을 종료합니다.")
        return

    # 3. 기준 파일 로드
    if os.path.exists(output_filepath):
        try:
            df_existing = pd.read_csv(output_filepath)
            print(f"기준 파일 로드 완료: {output_filename} ({len(df_existing)} 행)")
        except Exception as e:
            print(f"오류: 기준 파일({output_filepath}) 로드 중 문제 발생 - {e}")
            df_existing = pd.DataFrame()
            print(f"정보: 기준 파일 로드에 실패하여, 비어있는 상태로 병합을 시도합니다.")
    else:
        df_existing = pd.DataFrame()
        print(f"정보: 기준 파일({output_filename})이 없습니다. 새로 생성합니다.")

    # 4. 새로운 파일들 로드 및 컬럼 정렬
    new_dfs = []
    all_columns = set(df_existing.columns)

    temp_new_dfs_data = []
    for f_path in csv_files_to_merge:
        try:
            df_temp = pd.read_csv(f_path)
            temp_new_dfs_data.append({'path': f_path, 'df': df_temp})
            all_columns.update(df_temp.columns)
            print(f"파일 스캔 완료 (컬럼 수집): {os.path.basename(f_path)} ({len(df_temp)} 행, {len(df_temp.columns)} 열)")
        except Exception as e:
            print(f"경고: 파일 스캔 중 오류 발생 (컬럼 수집) - {os.path.basename(f_path)}: {e}")

    final_columns = list(df_existing.columns) + [col for col in all_columns if col not in df_existing.columns]

    for item in temp_new_dfs_data:
        f_path = item['path']
        df_new = item['df']
        try:
            df_new = df_new.reindex(columns=final_columns, fill_value=pd.NA)
            new_dfs.append(df_new)
            print(f"로드 및 컬럼 정렬 완료: {os.path.basename(f_path)} ({len(df_new)} 행)")
        except Exception as e: 
            print(f"오류: 파일 로드 또는 컬럼 정렬 중 - {os.path.basename(f_path)}: {e}")

    if not new_dfs:
        print("경고: 병합 가능한 유효한 데이터프레임이 없습니다.")
        return

    # 5. 병합 및 중복 제거 (기존 데이터를 우선 보존)
    if new_dfs:
        df_new_all = pd.concat(new_dfs, ignore_index=True)
    else:
        df_new_all = pd.DataFrame(columns=final_columns if final_columns else None)

    if df_existing.empty:
        df_merged = df_new_all
        if not df_merged.empty:
            if 'url' in df_merged.columns:
                df_merged.drop_duplicates(subset=['url'], keep='first', inplace=True)
            else:
                print("경고: 'url' 컬럼이 없어 중복 제거 생략.")
        print(f"정보: 기준 파일이 없어 새로 생성된 데이터 ({len(df_merged)} 행).")
    else:
        df_existing = df_existing.reindex(columns=final_columns, fill_value=pd.NA)
        df_new_all = df_new_all.reindex(columns=final_columns, fill_value=pd.NA)

        df_combined = pd.concat([df_existing, df_new_all], ignore_index=True)

        if 'url' in df_combined.columns:
            df_merged = df_combined.drop_duplicates(subset=['url'], keep='first')
            print(f"중복 제거 완료: 기존 데이터를 우선 보존하며 URL 기준 중복 제거.")
        else:
            df_merged = df_combined
            print("경고: 'url' 컬럼이 없어 중복 제거 생략.")

        df_existing_dedup_count = len(df_existing.drop_duplicates(subset=['url'], keep='first')) if 'url' in df_existing.columns else len(df_existing)
        added_rows = len(df_merged) - df_existing_dedup_count
        print(f"새로 추가된 행 (추정): {max(0, added_rows)}")

    # 6. 저장
    if not df_merged.empty:
        try:
            df_merged.to_csv(output_filepath, index=False, encoding="utf-8-sig")
            print(f"최종 병합된 파일 저장 완료: {output_filename} ({len(df_merged)} 행)")
        except Exception as e:
            print(f"오류: 최종 파일 저장 중 - {output_filepath}: {e}")
            return 
    else:
        print(f"정보: 병합 결과 데이터가 없어 {output_filename} 파일을 저장하지 않습니다.")

    # 7. 원본 CSV 삭제
    deleted_count = 0
    failed_to_delete = []
    if new_dfs:
        print("병합에 사용된 원본 CSV 파일 삭제 시작...")
        for f_path in csv_files_to_merge:
            try:
                os.remove(f_path)
                print(f"삭제됨: {os.path.basename(f_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"삭제 실패: {os.path.basename(f_path)} - {e}")
                failed_to_delete.append(os.path.basename(f_path))
        
        if failed_to_delete:
            print(f"경고: 다음 파일들은 삭제되지 못했습니다 - {', '.join(failed_to_delete)}")
        print(f"총 {deleted_count}개의 원본 파일 삭제 완료.")
    else:
        print("정보: 삭제할 원본 파일이 없습니다.")

    print(f"작업 완료: {directory_path} 디렉토리 처리 완료.")
