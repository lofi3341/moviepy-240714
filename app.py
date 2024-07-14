import streamlit as st
import numpy as np
import moviepy.editor as mp
import zipfile
from io import BytesIO
import tempfile
import os

try:
    import cv2
except ImportError as e:
    st.error(f"Error importing cv2: {e}")
    st.stop()

# 動画ファイルをアップロードする関数
def upload_videos(uploaded_files):
    return uploaded_files

# 動画を分割し、結合する関数
def process_and_merge_videos(uploaded_files):
    output_files = []
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name
        
        cap = cv2.VideoCapture(temp_file_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        output_file = BytesIO()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output_file:
            output_file_path = temp_output_file.name
        
        out = cv2.VideoWriter(output_file_path, fourcc, fps, (5760, 1080))

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            left_top = frame[:height//2, :width//2]
            right_top = frame[:height//2, width//2:]
            left_bottom = frame[height//2:, :width//2]

            combined_frame = np.hstack((left_top, right_top, left_bottom))
            out.write(combined_frame)

        cap.release()
        out.release()

        with open(output_file_path, 'rb') as f:
            output_file.write(f.read())
        output_file.seek(0)
        output_files.append(output_file)
        
        os.remove(temp_file_path)
        os.remove(output_file_path)

    return output_files

# 動画から音声を抽出する関数
def extract_audio(uploaded_file):
    audio_file = BytesIO()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
        temp_video_file.write(uploaded_file.getbuffer())
        temp_video_path = temp_video_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        temp_audio_path = temp_audio_file.name
    
    clip = mp.VideoFileClip(temp_video_path)
    clip.audio.write_audiofile(temp_audio_path, codec='pcm_s16le')

    with open(temp_audio_path, 'rb') as f:
        audio_file.write(f.read())
    audio_file.seek(0)

    os.remove(temp_video_path)
    os.remove(temp_audio_path)
    
    return audio_file

# 音声を挿入する関数
def insert_audio(uploaded_file, audio_file):
    output_file = BytesIO()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
        temp_video_file.write(uploaded_file.getbuffer())
        temp_video_path = temp_video_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        temp_audio_file.write(audio_file.getbuffer())
        temp_audio_path = temp_audio_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output_file:
        temp_output_path = temp_output_file.name
    
    video_clip = mp.VideoFileClip(temp_video_path)
    audio_clip = mp.AudioFileClip(temp_audio_path)

    final_clip = video_clip.set_audio(audio_clip)
    
    try:
        final_clip.write_videofile(temp_output_path, codec='libx264', audio_codec='aac', verbose=True, logger='bar')
    except Exception as e:
        st.error(f"Error writing video file: {e}")
    
    with open(temp_output_path, 'rb') as f:
        output_file.write(f.read())
    output_file.seek(0)

    os.remove(temp_video_path)
    os.remove(temp_audio_path)
    os.remove(temp_output_path)
    
    return output_file

# 動画を指定したサイズに変換する関数
def resize_video(uploaded_file, width, height):
    output_file = BytesIO()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
        temp_video_file.write(uploaded_file.getbuffer())
        temp_video_path = temp_video_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_output_file:
        temp_output_path = temp_output_file.name
    
    clip = mp.VideoFileClip(temp_video_path)
    resized_clip = clip.resize((width, height))
    resized_clip.write_videofile(temp_output_path, codec='libx264', audio_codec='aac', verbose=True, logger='bar')

    with open(temp_output_path, 'rb') as f:
        output_file.write(f.read())
    output_file.seek(0)

    os.remove(temp_video_path)
    os.remove(temp_output_path)
    
    return output_file

# 全ての出力動画をzipアーカイブにまとめる関数
def create_zip(video_files, zip_name):
    zip_file = BytesIO()
    with zipfile.ZipFile(zip_file, 'w') as zipf:
        for i, video_file in enumerate(video_files):
            video_file.seek(0)
            zipf.writestr(f"video_{i}.mp4", video_file.read())
    zip_file.seek(0)
    return zip_file

# Streamlitインターフェース
st.title("動画分割・結合・音声挿入アプリ")
st.write("App started successfully")

uploaded_files = st.file_uploader("動画ファイルをアップロード", type=["mp4", "mov", "avi"], accept_multiple_files=True)
if uploaded_files:
    st.session_state.uploaded_videos = upload_videos(uploaded_files)
    st.write("Videos uploaded successfully")

if st.button("変換"):
    st.write("Processing videos")
    if 'uploaded_videos' in st.session_state:
        output_files = process_and_merge_videos(st.session_state.uploaded_videos)

        extracted_audio_files = []
        for uploaded_file in st.session_state.uploaded_videos:
            audio_file = extract_audio(uploaded_file)
            extracted_audio_files.append(audio_file)

        output_with_audio_files = []
        for uploaded_file, audio_file in zip(output_files, extracted_audio_files):
            output_file = insert_audio(uploaded_file, audio_file)
            output_with_audio_files.append(output_file)

        st.session_state.converted_videos = output_with_audio_files
        st.write("Videos processed successfully")

if 'converted_videos' in st.session_state:
    st.subheader("変換された動画")
    for i, video in enumerate(st.session_state.converted_videos):
        video.seek(0)
        st.download_button(label=f"動画 {i+1} をダウンロード", data=video, file_name=f"converted_video_{i+1}.mp4", mime="video/mp4")

    if st.button("動画を2880x540に変換しまとめてzipでダウンロード"):
        st.write("Resizing videos to 2880x540")
        resized_videos = []
        for video in st.session_state.converted_videos:
            resized_video = resize_video(video, 2880, 540)
            resized_videos.append(resized_video)
        zip_file = create_zip(resized_videos, "resized_videos_2880x540.zip")
        zip_file.seek(0)
        st.download_button(label="全動画を2880x540に変換しzipでダウンロード", data=zip_file, file_name="resized_videos_2880x540.zip", mime="application/zip")

    if st.button("動画を1920x360に変換しまとめてzipでダウンロード"):
        st.write("Resizing videos to 1920x360")
        resized_videos = []
        for video in st.session_state.converted_videos:
            resized_video = resize_video(video, 1920, 360)
            resized_videos.append(resized_video)
        zip_file = create_zip(resized_videos, "resized_videos_1920x360.zip")
        zip_file.seek(0)
        st.download_button(label="全動画を1920x360に変換しzipでダウンロード", data=zip_file, file_name="resized_videos_1920x360.zip", mime="application/zip")
