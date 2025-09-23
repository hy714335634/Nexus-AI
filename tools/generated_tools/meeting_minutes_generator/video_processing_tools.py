from typing import Dict, List, Optional, Any, Tuple, Union
import os
import json
import tempfile
import subprocess
from pathlib import Path
import logging
import ffmpeg
import boto3
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def extract_audio_from_video(
    video_path: str,
    output_path: Optional[str] = None,
    audio_format: str = "wav",
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    audio_quality: str = "medium",
    overwrite: bool = False
) -> str:
    """
    Extract audio from video files using FFmpeg.
    
    Args:
        video_path: Path to the input video file
        output_path: Path to save the extracted audio (if None, auto-generated based on video filename)
        audio_format: Output audio format (wav, mp3, aac, etc.)
        start_time: Start time in seconds to begin extraction (optional)
        end_time: End time in seconds to stop extraction (optional)
        audio_quality: Audio quality setting (low, medium, high)
        overwrite: Whether to overwrite existing output file
        
    Returns:
        JSON string with extraction results and output file path
    """
    try:
        # Validate video file
        if not os.path.exists(video_path):
            return json.dumps({
                "success": False,
                "error": f"Video file not found: {video_path}",
                "error_type": "file_not_found"
            })
        
        # Get video info
        try:
            probe = ffmpeg.probe(video_path)
            video_info = next((stream for stream in probe['streams'] 
                              if stream['codec_type'] == 'video'), None)
            audio_streams = [stream for stream in probe['streams'] 
                            if stream['codec_type'] == 'audio']
            
            if not audio_streams:
                return json.dumps({
                    "success": False,
                    "error": "No audio stream found in the video file",
                    "error_type": "no_audio_stream"
                })
                
            # Get video duration
            duration = float(probe['format']['duration'])
            
        except ffmpeg.Error as e:
            return json.dumps({
                "success": False,
                "error": f"Error probing video file: {str(e)}",
                "error_type": "probe_error"
            })
        
        # Generate output path if not provided
        if not output_path:
            video_filename = os.path.basename(video_path)
            video_name = os.path.splitext(video_filename)[0]
            output_path = f"{video_name}.{audio_format}"
        
        # Check if output file exists and handle overwrite flag
        if os.path.exists(output_path) and not overwrite:
            return json.dumps({
                "success": False,
                "error": f"Output file already exists: {output_path}. Use overwrite=True to replace.",
                "error_type": "file_exists"
            })
        
        # Set quality parameters based on audio_quality
        quality_params = {
            "low": {"b:a": "64k"},
            "medium": {"b:a": "128k"},
            "high": {"b:a": "256k"}
        }.get(audio_quality.lower(), {"b:a": "128k"})
        
        # Build the FFmpeg command
        stream = ffmpeg.input(video_path)
        
        # Apply time filters if specified
        if start_time is not None or end_time is not None:
            stream = stream.trim(start=start_time, end=end_time).filter('asetpts', 'PTS-STARTPTS')
        
        # Set output parameters
        stream = stream.audio
        output_args = quality_params
        
        # Run the extraction
        try:
            stream = ffmpeg.output(stream, output_path, **output_args)
            ffmpeg.run(stream, quiet=True, overwrite_output=overwrite)
        except ffmpeg.Error as e:
            return json.dumps({
                "success": False,
                "error": f"FFmpeg error: {str(e)}",
                "error_type": "ffmpeg_error"
            })
        
        # Get output file info
        output_size = os.path.getsize(output_path)
        
        return json.dumps({
            "success": True,
            "output_path": output_path,
            "format": audio_format,
            "duration": duration if start_time is None and end_time is None else 
                       (min(duration, end_time or duration) - (start_time or 0)),
            "file_size_bytes": output_size,
            "audio_quality": audio_quality,
            "original_video": video_path
        })
        
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        })

@tool
def transcribe_audio(
    audio_path: str,
    language_code: str = "zh-CN",
    enable_speaker_diarization: bool = True,
    max_speakers: int = 10,
    output_format: str = "json",
    vocabulary_filter_method: Optional[str] = None,
    vocabulary_filter_names: Optional[List[str]] = None,
    custom_vocabulary: Optional[List[str]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Transcribe audio to text using AWS Transcribe service with speaker diarization.
    
    Args:
        audio_path: Path to the audio file to transcribe
        language_code: Language code (e.g., zh-CN for Chinese, en-US for English)
        enable_speaker_diarization: Whether to identify different speakers in the audio
        max_speakers: Maximum number of speakers to identify (when diarization is enabled)
        output_format: Output format (json or text)
        vocabulary_filter_method: Optional vocabulary filter method (mask, remove, tag)
        vocabulary_filter_names: Optional list of vocabulary filter names
        custom_vocabulary: Optional list of custom vocabulary words
        output_path: Path to save the transcription results (if None, only returns the result)
        
    Returns:
        JSON string with transcription results including speaker identification
    """
    try:
        # Validate audio file
        if not os.path.exists(audio_path):
            return json.dumps({
                "success": False,
                "error": f"Audio file not found: {audio_path}",
                "error_type": "file_not_found"
            })
        
        # Create AWS Transcribe client
        transcribe = boto3.client('transcribe', region_name='us-east-1')
        
        # Generate a unique job name
        job_name = f"transcription_{os.path.basename(audio_path).replace('.', '_')}_{int(os.path.getmtime(audio_path))}"
        
        # Upload audio file to S3 (temporary)
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = "meeting-minutes-temp-audio"
        
        try:
            # Check if bucket exists, create if not
            try:
                s3.head_bucket(Bucket=bucket_name)
            except:
                s3.create_bucket(Bucket=bucket_name)
                
            # Upload file
            object_key = f"uploads/{os.path.basename(audio_path)}"
            s3.upload_file(audio_path, bucket_name, object_key)
            s3_uri = f"s3://{bucket_name}/{object_key}"
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error uploading to S3: {str(e)}",
                "error_type": "s3_upload_error"
            })
        
        # Prepare transcription job parameters
        transcription_settings = {
            'TranscriptionJobName': job_name,
            'Media': {'MediaFileUri': s3_uri},
            'MediaFormat': os.path.splitext(audio_path)[1][1:].lower(),
            'LanguageCode': language_code,
            'OutputBucketName': bucket_name,
            'OutputKey': f"transcripts/{job_name}.json"
        }
        
        # Add speaker diarization if enabled
        if enable_speaker_diarization:
            transcription_settings['Settings'] = {
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': max_speakers
            }
        
        # Add vocabulary filters if provided
        if vocabulary_filter_method and vocabulary_filter_names:
            transcription_settings['Settings'] = transcription_settings.get('Settings', {})
            transcription_settings['Settings']['VocabularyFilterMethod'] = vocabulary_filter_method
            transcription_settings['Settings']['VocabularyFilterNames'] = vocabulary_filter_names
        
        # Add custom vocabulary if provided
        if custom_vocabulary:
            # Create a custom vocabulary
            vocab_name = f"vocab_{job_name}"
            try:
                transcribe.create_vocabulary(
                    VocabularyName=vocab_name,
                    LanguageCode=language_code,
                    Phrases=custom_vocabulary
                )
                # Wait for vocabulary to be ready
                waiter = transcribe.get_waiter('vocabulary_ready')
                waiter.wait(VocabularyName=vocab_name)
                
                # Add to transcription settings
                transcription_settings['Settings'] = transcription_settings.get('Settings', {})
                transcription_settings['Settings']['VocabularyName'] = vocab_name
                
            except Exception as e:
                logger.warning(f"Failed to create custom vocabulary: {str(e)}")
        
        # Start transcription job
        try:
            transcribe.start_transcription_job(**transcription_settings)
            
            # Wait for completion
            while True:
                status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
                job_status = status['TranscriptionJob']['TranscriptionJobStatus']
                
                if job_status in ['COMPLETED', 'FAILED']:
                    break
                    
                import time
                time.sleep(5)
                
            if job_status == 'FAILED':
                failure_reason = status['TranscriptionJob'].get('FailureReason', 'Unknown reason')
                return json.dumps({
                    "success": False,
                    "error": f"Transcription job failed: {failure_reason}",
                    "error_type": "transcription_failed"
                })
                
            # Get the transcript
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
            # Download the transcript
            transcript_path = os.path.join(tempfile.gettempdir(), f"{job_name}_transcript.json")
            s3.download_file(
                bucket_name, 
                f"transcripts/{job_name}.json", 
                transcript_path
            )
            
            # Read the transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
            
            # Process the transcript based on output format
            if output_format.lower() == 'text':
                # Simple text output without speaker information
                transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                result = {
                    "success": True,
                    "transcript": transcript_text,
                    "language_code": language_code,
                    "audio_duration": transcript_data['results'].get('audio_duration', 0)
                }
            else:
                # Full JSON output with speaker information if available
                result = {
                    "success": True,
                    "transcript": transcript_data['results']['transcripts'][0]['transcript'],
                    "language_code": language_code,
                    "audio_duration": transcript_data['results'].get('audio_duration', 0)
                }
                
                # Include speaker information if available
                if enable_speaker_diarization and 'speaker_labels' in transcript_data['results']:
                    speakers = transcript_data['results']['speaker_labels']['speakers']
                    segments = transcript_data['results']['speaker_labels']['segments']
                    items = transcript_data['results']['items']
                    
                    # Process segments with speaker information
                    speaker_segments = []
                    for segment in segments:
                        speaker_label = segment['speaker_label']
                        start_time = float(segment['start_time'])
                        end_time = float(segment['end_time'])
                        
                        # Find items in this segment
                        segment_items = []
                        for item in items:
                            if 'start_time' not in item:
                                continue
                                
                            item_start = float(item['start_time'])
                            if item_start >= start_time and item_start <= end_time:
                                segment_items.append(item['alternatives'][0]['content'])
                        
                        segment_text = ' '.join(segment_items)
                        speaker_segments.append({
                            "speaker": speaker_label,
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": segment_text
                        })
                    
                    result["speaker_count"] = len(speakers)
                    result["speaker_segments"] = speaker_segments
            
            # Save to output file if specified
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    if output_format.lower() == 'text':
                        f.write(result["transcript"])
                    else:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                
                result["output_path"] = output_path
            
            # Clean up
            try:
                os.remove(transcript_path)
                s3.delete_object(Bucket=bucket_name, Key=object_key)
                s3.delete_object(Bucket=bucket_name, Key=f"transcripts/{job_name}.json")
                transcribe.delete_transcription_job(TranscriptionJobName=job_name)
                
                if custom_vocabulary:
                    try:
                        transcribe.delete_vocabulary(VocabularyName=vocab_name)
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Cleanup error (non-critical): {str(e)}")
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Transcription error: {str(e)}",
                "error_type": "transcription_error"
            })
            
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        })

@tool
def generate_meeting_minutes(
    transcript: str,
    meeting_title: Optional[str] = None,
    meeting_date: Optional[str] = None,
    participants: Optional[List[str]] = None,
    format_type: str = "standard",
    language: str = "zh-CN",
    output_path: Optional[str] = None
) -> str:
    """
    Generate meeting minutes from transcript using AWS Bedrock.
    
    Args:
        transcript: Transcript text or path to transcript JSON file
        meeting_title: Title of the meeting (optional)
        meeting_date: Date of the meeting (optional)
        participants: List of meeting participants (optional)
        format_type: Format type (standard, detailed, summary)
        language: Language code for the output (zh-CN for Chinese, en-US for English)
        output_path: Path to save the generated minutes (if None, only returns the result)
        
    Returns:
        JSON string with generated meeting minutes
    """
    try:
        # Check if transcript is a file path
        if os.path.exists(transcript):
            try:
                with open(transcript, 'r', encoding='utf-8') as f:
                    if transcript.lower().endswith('.json'):
                        # Parse JSON file
                        transcript_data = json.load(f)
                        if isinstance(transcript_data, dict) and 'transcript' in transcript_data:
                            transcript_text = transcript_data['transcript']
                        elif isinstance(transcript_data, dict) and 'results' in transcript_data:
                            # AWS Transcribe format
                            transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                        else:
                            return json.dumps({
                                "success": False,
                                "error": "Invalid transcript JSON format",
                                "error_type": "invalid_format"
                            })
                    else:
                        # Plain text file
                        transcript_text = f.read()
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Error reading transcript file: {str(e)}",
                    "error_type": "file_read_error"
                })
        else:
            # Assume transcript is the actual text
            transcript_text = transcript
        
        # Validate transcript
        if not transcript_text or len(transcript_text.strip()) < 10:
            return json.dumps({
                "success": False,
                "error": "Transcript is too short or empty",
                "error_type": "invalid_transcript"
            })
        
        # Create AWS Bedrock client
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Prepare the prompt based on format type
        format_descriptions = {
            "standard": "标准格式的会议纪要，包含会议基本信息、讨论要点、决策和行动项",
            "detailed": "详细的会议纪要，包含完整的讨论内容、决策过程和详细的行动项",
            "summary": "简洁的会议纪要摘要，只包含最重要的讨论点和决策"
        }
        
        format_description = format_descriptions.get(format_type.lower(), format_descriptions["standard"])
        
        # Build meeting context
        meeting_context = ""
        if meeting_title:
            meeting_context += f"会议标题: {meeting_title}\n"
        if meeting_date:
            meeting_context += f"会议日期: {meeting_date}\n"
        if participants:
            meeting_context += f"参会人员: {', '.join(participants)}\n"
        
        # Build the prompt
        language_prompt = "使用中文" if language.startswith("zh") else "使用英语"
        
        prompt = f"""你是一位专业的会议纪要整理专家。请根据以下会议记录生成一份{format_description}。{language_prompt}回复。

会议信息:
{meeting_context}

会议记录:
{transcript_text[:50000]}  # Limit to 50K characters to avoid token limits

请生成包含以下部分的会议纪要:
1. 会议基本信息（标题、日期、参与者）
2. 会议议程/主题
3. 讨论要点（按主题组织）
4. 重要决策
5. 行动项（包括负责人和截止日期，如有提及）
6. 后续事项

请使用清晰的结构和标题，确保纪要专业、准确、易于阅读。只包含会议记录中明确提及的内容，不要添加未在记录中出现的信息。"""

        # Invoke Claude model
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        minutes_text = response_body['content'][0]['text']
        
        # Save to output file if specified
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minutes_text)
        
        # Prepare result
        result = {
            "success": True,
            "meeting_minutes": minutes_text,
            "format_type": format_type,
            "language": language
        }
        
        if output_path:
            result["output_path"] = output_path
            
        if meeting_title:
            result["meeting_title"] = meeting_title
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error generating meeting minutes: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        })

@tool
def process_video_to_minutes(
    video_path: str,
    meeting_title: Optional[str] = None,
    meeting_date: Optional[str] = None,
    participants: Optional[List[str]] = None,
    language_code: str = "zh-CN",
    format_type: str = "standard",
    output_dir: Optional[str] = None,
    cleanup_temp_files: bool = True
) -> str:
    """
    Process a video file to generate meeting minutes in one step.
    
    This tool combines audio extraction, transcription, and meeting minutes generation.
    
    Args:
        video_path: Path to the video file
        meeting_title: Title of the meeting (optional)
        meeting_date: Date of the meeting (optional)
        participants: List of meeting participants (optional)
        language_code: Language code for transcription and output
        format_type: Meeting minutes format (standard, detailed, summary)
        output_dir: Directory to save output files (if None, uses same directory as video)
        cleanup_temp_files: Whether to delete temporary files after processing
        
    Returns:
        JSON string with processing results and paths to output files
    """
    try:
        # Validate video file
        if not os.path.exists(video_path):
            return json.dumps({
                "success": False,
                "error": f"Video file not found: {video_path}",
                "error_type": "file_not_found"
            })
        
        # Create output directory if needed
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.dirname(video_path) or "."
        
        # Generate file names
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        audio_path = os.path.join(output_dir, f"{video_name}.wav")
        transcript_path = os.path.join(output_dir, f"{video_name}_transcript.json")
        minutes_path = os.path.join(output_dir, f"{video_name}_minutes.md")
        
        # Step 1: Extract audio
        logger.info(f"Extracting audio from {video_path}")
        audio_result = json.loads(extract_audio_from_video(
            video_path=video_path,
            output_path=audio_path,
            audio_format="wav",
            audio_quality="high",
            overwrite=True
        ))
        
        if not audio_result.get("success"):
            return json.dumps({
                "success": False,
                "error": f"Audio extraction failed: {audio_result.get('error')}",
                "error_type": audio_result.get('error_type', 'audio_extraction_error'),
                "step": "audio_extraction"
            })
        
        # Step 2: Transcribe audio
        logger.info(f"Transcribing audio from {audio_path}")
        transcribe_result = json.loads(transcribe_audio(
            audio_path=audio_path,
            language_code=language_code,
            enable_speaker_diarization=True,
            output_format="json",
            output_path=transcript_path
        ))
        
        if not transcribe_result.get("success"):
            return json.dumps({
                "success": False,
                "error": f"Transcription failed: {transcribe_result.get('error')}",
                "error_type": transcribe_result.get('error_type', 'transcription_error'),
                "step": "transcription",
                "audio_result": audio_result
            })
        
        # Step 3: Generate meeting minutes
        logger.info(f"Generating meeting minutes from transcript")
        minutes_result = json.loads(generate_meeting_minutes(
            transcript=transcript_path,
            meeting_title=meeting_title,
            meeting_date=meeting_date,
            participants=participants,
            format_type=format_type,
            language=language_code,
            output_path=minutes_path
        ))
        
        if not minutes_result.get("success"):
            return json.dumps({
                "success": False,
                "error": f"Meeting minutes generation failed: {minutes_result.get('error')}",
                "error_type": minutes_result.get('error_type', 'minutes_generation_error'),
                "step": "minutes_generation",
                "audio_result": audio_result,
                "transcribe_result": transcribe_result
            })
        
        # Clean up temporary files if requested
        if cleanup_temp_files:
            try:
                os.remove(audio_path)
                logger.info(f"Removed temporary audio file: {audio_path}")
            except:
                logger.warning(f"Failed to remove temporary audio file: {audio_path}")
        
        # Prepare final result
        result = {
            "success": True,
            "video_path": video_path,
            "transcript_path": transcript_path,
            "minutes_path": minutes_path,
            "meeting_title": meeting_title,
            "language": language_code,
            "format_type": format_type,
            "audio_duration": transcribe_result.get("audio_duration"),
            "transcript_length": len(transcribe_result.get("transcript", "")),
            "minutes_text": minutes_result.get("meeting_minutes")
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in video processing pipeline: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        })

@tool
def validate_video_file(
    video_path: str,
    check_audio: bool = True
) -> str:
    """
    Validate a video file and check if it contains audio streams.
    
    Args:
        video_path: Path to the video file to validate
        check_audio: Whether to check for audio streams
        
    Returns:
        JSON string with validation results and video metadata
    """
    try:
        # Check if file exists
        if not os.path.exists(video_path):
            return json.dumps({
                "valid": False,
                "error": f"File not found: {video_path}",
                "error_type": "file_not_found"
            })
        
        # Get file extension
        _, ext = os.path.splitext(video_path)
        ext = ext.lower()[1:]  # Remove the dot
        
        # Check if extension is supported
        supported_formats = ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"]
        if ext not in supported_formats:
            return json.dumps({
                "valid": False,
                "error": f"Unsupported video format: {ext}. Supported formats: {', '.join(supported_formats)}",
                "error_type": "unsupported_format",
                "file_extension": ext
            })
        
        # Probe the video file
        try:
            probe = ffmpeg.probe(video_path)
            
            # Check for video streams
            video_streams = [stream for stream in probe['streams'] 
                            if stream['codec_type'] == 'video']
            
            if not video_streams:
                return json.dumps({
                    "valid": False,
                    "error": "No video streams found in the file",
                    "error_type": "no_video_stream"
                })
            
            # Check for audio streams if requested
            if check_audio:
                audio_streams = [stream for stream in probe['streams'] 
                                if stream['codec_type'] == 'audio']
                
                if not audio_streams:
                    return json.dumps({
                        "valid": False,
                        "error": "No audio streams found in the video file",
                        "error_type": "no_audio_stream"
                    })
            
            # Extract video metadata
            video_info = video_streams[0]
            format_info = probe['format']
            
            # Prepare result
            result = {
                "valid": True,
                "file_path": video_path,
                "file_size_bytes": os.path.getsize(video_path),
                "format": format_info.get('format_name', ext),
                "duration_seconds": float(format_info.get('duration', 0)),
                "bitrate": int(format_info.get('bit_rate', 0)),
                "video_codec": video_info.get('codec_name', 'unknown'),
                "width": int(video_info.get('width', 0)),
                "height": int(video_info.get('height', 0)),
                "has_audio": bool(audio_streams) if check_audio else None
            }
            
            # Add audio info if available
            if check_audio and audio_streams:
                audio_info = audio_streams[0]
                result["audio_codec"] = audio_info.get('codec_name', 'unknown')
                result["audio_channels"] = int(audio_info.get('channels', 0))
                result["audio_sample_rate"] = int(audio_info.get('sample_rate', 0))
            
            return json.dumps(result)
            
        except ffmpeg.Error as e:
            return json.dumps({
                "valid": False,
                "error": f"Error probing video file: {str(e)}",
                "error_type": "probe_error"
            })
            
    except Exception as e:
        logger.error(f"Error validating video file: {str(e)}")
        return json.dumps({
            "valid": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        })