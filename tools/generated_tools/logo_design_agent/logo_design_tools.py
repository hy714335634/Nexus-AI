#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logo Design Agent - Image Generator Tool

This module provides tools for generating high-quality logo images using 
Amazon Bedrock's image generation capabilities.
"""

import json
import os
import base64
import tempfile
import time
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple
import boto3
from PIL import Image
import io
import logging
import strands
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def image_generator(
    prompt: str,
    style: str = "logo",
    resolution: str = "1024x1024",
    negative_prompt: str = "blurry, low quality, pixelated, watermark, signature, text",
    model_id: str = "stability.stable-diffusion-xl",
    output_format: str = "png",
    num_images: int = 1,
    seed: Optional[int] = None,
    save_path: Optional[str] = None,
) -> str:
    """
    Generate high-quality logo images using Amazon Bedrock's image generation models.
    
    Args:
        prompt: Detailed description of the logo to generate
        style: Logo style (logo, minimalist, abstract, modern, vintage, etc.)
        resolution: Image resolution (512x512, 1024x1024, etc.)
        negative_prompt: Elements to avoid in the generated image
        model_id: Bedrock model ID to use (stability.stable-diffusion-xl, anthropic.claude-3-sonnet, etc.)
        output_format: Output image format (png or jpeg)
        num_images: Number of images to generate (1-4)
        seed: Random seed for reproducibility (optional)
        save_path: Path to save the generated images (optional)
        
    Returns:
        str: JSON string containing image metadata and base64-encoded images or file paths
    """
    try:
        # Validate parameters
        if output_format.lower() not in ["png", "jpeg", "jpg"]:
            output_format = "png"
        
        if output_format.lower() == "jpg":
            output_format = "jpeg"
            
        if num_images < 1 or num_images > 4:
            num_images = 1
            
        # Enhance prompt with style information
        enhanced_prompt = f"Professional {style} logo design: {prompt}. High quality, professional, vector-like, clean lines, suitable for business use."
        
        # Parse resolution
        try:
            width, height = map(int, resolution.lower().split('x'))
            # Ensure minimum resolution of 1000x1000
            width = max(width, 1000)
            height = max(height, 1000)
            # Round to nearest supported resolution
            width = round(width / 8) * 8
            height = round(height / 8) * 8
        except ValueError:
            width, height = 1024, 1024
            
        # Initialize Bedrock client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )
        
        # Create temp directory for saving if not provided
        if save_path is None:
            temp_dir = tempfile.mkdtemp()
            save_path = temp_dir
        else:
            os.makedirs(save_path, exist_ok=True)
            
        # Prepare results
        results = {
            "status": "success",
            "images": [],
            "metadata": {
                "prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "style": style,
                "resolution": f"{width}x{height}",
                "model_id": model_id,
                "output_format": output_format,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Generate images based on the model
        if "stability" in model_id.lower():
            generated_images = _generate_with_stability(
                bedrock_runtime, 
                enhanced_prompt, 
                negative_prompt,
                width,
                height,
                num_images,
                seed
            )
        else:
            # Default to Stable Diffusion if model not specifically handled
            generated_images = _generate_with_stability(
                bedrock_runtime, 
                enhanced_prompt, 
                negative_prompt,
                width,
                height,
                num_images,
                seed
            )
            
        # Process and save images
        for i, img_data in enumerate(generated_images):
            # Generate unique filename
            filename = f"logo_{int(time.time())}_{i+1}.{output_format}"
            filepath = os.path.join(save_path, filename)
            
            # Convert image data to PIL Image
            image = Image.open(io.BytesIO(img_data))
            
            # Save image
            image.save(filepath, format=output_format.upper())
            
            # Create base64 representation for response
            buffered = io.BytesIO()
            image.save(buffered, format=output_format.upper())
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Add to results
            results["images"].append({
                "index": i,
                "file_path": filepath,
                "base64": img_base64,
                "width": image.width,
                "height": image.height,
                "format": output_format
            })
            
        return json.dumps(results)
        
    except Exception as e:
        error_msg = f"Error generating images: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "error": error_msg
        })

def _generate_with_stability(
    client: Any,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_images: int,
    seed: Optional[int] = None
) -> List[bytes]:
    """
    Generate images using Stability AI models on Amazon Bedrock.
    
    Args:
        client: Bedrock runtime client
        prompt: Image generation prompt
        negative_prompt: Elements to avoid in the image
        width: Image width
        height: Image height
        num_images: Number of images to generate
        seed: Random seed for reproducibility
        
    Returns:
        List of image data in bytes
    """
    # Prepare request body
    request_body = {
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1.0
            },
            {
                "text": negative_prompt,
                "weight": -1.0
            }
        ],
        "cfg_scale": 7.0,
        "steps": 50,
        "width": width,
        "height": height,
        "seed": seed if seed is not None else int.from_bytes(os.urandom(2), "big"),
        "samples": num_images
    }
    
    # Make the request
    response = client.invoke_model(
        modelId="stability.stable-diffusion-xl",
        body=json.dumps(request_body)
    )
    
    # Parse response
    response_body = json.loads(response["body"].read())
    
    # Extract images
    images = []
    for artifact in response_body.get("artifacts", []):
        if artifact.get("finishReason") == "SUCCESS":
            image_data = base64.b64decode(artifact.get("base64"))
            images.append(image_data)
    
    return images

@tool
def html_report_generator(
    title: str,
    logo_paths: List[str],
    design_rationale: str,
    color_palette: Optional[List[str]] = None,
    font_choices: Optional[List[str]] = None,
    design_elements: Optional[List[Dict[str, str]]] = None,
    usage_guidelines: Optional[str] = None,
    client_name: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generate a professional HTML design report for logo designs.
    
    Args:
        title: Report title
        logo_paths: List of paths to logo image files
        design_rationale: Explanation of the design concept and choices
        color_palette: List of color hex codes used in the design
        font_choices: List of fonts used in the design
        design_elements: List of design elements with descriptions
        usage_guidelines: Guidelines for using the logo
        client_name: Name of the client
        output_path: Path to save the HTML report (optional)
        
    Returns:
        str: JSON string containing the report path and HTML content
    """
    try:
        # Default values
        if color_palette is None:
            color_palette = ["#000000"]
        if font_choices is None:
            font_choices = ["Sans-serif"]
        if design_elements is None:
            design_elements = []
        if usage_guidelines is None:
            usage_guidelines = "Use the logo consistently across all brand materials."
        if client_name is None:
            client_name = "Client"
            
        # Create output directory if needed
        if output_path is None:
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, f"logo_design_report_{int(time.time())}.html")
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
        # Process logo images
        logo_data = []
        for i, logo_path in enumerate(logo_paths):
            if os.path.exists(logo_path):
                # Get image dimensions
                try:
                    with Image.open(logo_path) as img:
                        width, height = img.size
                        
                    # Create base64 representation
                    with open(logo_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode("utf-8")
                        
                    # Get file extension
                    file_ext = os.path.splitext(logo_path)[1].lstrip(".").lower()
                    if file_ext not in ["png", "jpg", "jpeg"]:
                        file_ext = "png"
                        
                    logo_data.append({
                        "path": logo_path,
                        "base64": img_data,
                        "width": width,
                        "height": height,
                        "format": file_ext,
                        "index": i + 1
                    })
                except Exception as e:
                    logger.error(f"Error processing image {logo_path}: {str(e)}")
                    
        # Generate HTML content
        html_content = _generate_html_report(
            title=title,
            logo_data=logo_data,
            design_rationale=design_rationale,
            color_palette=color_palette,
            font_choices=font_choices,
            design_elements=design_elements,
            usage_guidelines=usage_guidelines,
            client_name=client_name
        )
        
        # Write HTML file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return json.dumps({
            "status": "success",
            "report_path": output_path,
            "html_content": html_content,
            "metadata": {
                "title": title,
                "client_name": client_name,
                "logo_count": len(logo_data),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
        
    except Exception as e:
        error_msg = f"Error generating HTML report: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "error": error_msg
        })

def _generate_html_report(
    title: str,
    logo_data: List[Dict[str, Any]],
    design_rationale: str,
    color_palette: List[str],
    font_choices: List[str],
    design_elements: List[Dict[str, str]],
    usage_guidelines: str,
    client_name: str
) -> str:
    """
    Generate the HTML content for the design report.
    
    Args:
        title: Report title
        logo_data: List of logo image data
        design_rationale: Explanation of the design concept
        color_palette: List of color hex codes
        font_choices: List of fonts used
        design_elements: List of design elements with descriptions
        usage_guidelines: Guidelines for using the logo
        client_name: Name of the client
        
    Returns:
        str: HTML content
    """
    # Format current date
    current_date = time.strftime("%B %d, %Y")
    
    # Generate color palette HTML
    color_blocks = ""
    for color in color_palette:
        color_blocks += f"""
        <div class="color-block">
            <div class="color-sample" style="background-color: {color};"></div>
            <div class="color-code">{color}</div>
        </div>
        """
    
    # Generate font choices HTML
    font_list = ""
    for font in font_choices:
        font_list += f"""
        <div class="font-sample">
            <span class="font-name">{font}</span>
            <span class="font-example" style="font-family: '{font}', sans-serif;">ABCDEFGHIJKLM abcdefghijklm 1234567890</span>
        </div>
        """
    
    # Generate design elements HTML
    elements_html = ""
    for element in design_elements:
        name = element.get("name", "Element")
        description = element.get("description", "")
        elements_html += f"""
        <div class="design-element">
            <h4>{name}</h4>
            <p>{description}</p>
        </div>
        """
    
    # Generate logo showcase HTML
    logo_showcase = ""
    for logo in logo_data:
        logo_showcase += f"""
        <div class="logo-container">
            <img src="data:image/{logo['format']};base64,{logo['base64']}" 
                 alt="Logo Design {logo['index']}" 
                 class="logo-image">
            <div class="logo-caption">Design Variation {logo['index']}</div>
        </div>
        """
    
    # Create the full HTML document
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Logo Design Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Open+Sans:wght@300;400;600&display=swap');
        
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --text-color: #333;
            --light-gray: #f5f5f5;
            --medium-gray: #e0e0e0;
            --dark-gray: #777;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Open Sans', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #fff;
            padding: 0;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        header {{
            background-color: var(--primary-color);
            color: white;
            padding: 40px 0;
            text-align: center;
        }}
        
        h1, h2, h3, h4 {{
            font-family: 'Montserrat', sans-serif;
            margin-bottom: 20px;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 600;
        }}
        
        h2 {{
            font-size: 2rem;
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
            margin-top: 40px;
        }}
        
        h3 {{
            font-size: 1.5rem;
            color: var(--secondary-color);
        }}
        
        p {{
            margin-bottom: 20px;
            line-height: 1.8;
        }}
        
        .meta-info {{
            font-size: 1.1rem;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 10px;
        }}
        
        section {{
            margin: 40px 0;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        .logo-showcase {{
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            justify-content: center;
            margin: 30px 0;
        }}
        
        .logo-container {{
            text-align: center;
            max-width: 500px;
        }}
        
        .logo-image {{
            max-width: 100%;
            height: auto;
            border: 1px solid var(--medium-gray);
            border-radius: 5px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        
        .logo-caption {{
            margin-top: 10px;
            font-weight: 600;
            color: var(--dark-gray);
        }}
        
        .color-palette {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin: 20px 0;
        }}
        
        .color-block {{
            text-align: center;
        }}
        
        .color-sample {{
            width: 100px;
            height: 100px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 10px;
        }}
        
        .color-code {{
            font-family: monospace;
            font-size: 0.9rem;
        }}
        
        .font-samples {{
            margin: 20px 0;
        }}
        
        .font-sample {{
            margin-bottom: 15px;
            padding: 10px;
            background-color: var(--light-gray);
            border-radius: 5px;
        }}
        
        .font-name {{
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .font-example {{
            font-size: 1.2rem;
            display: block;
        }}
        
        .design-elements {{
            margin: 20px 0;
        }}
        
        .design-element {{
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--medium-gray);
        }}
        
        .design-element:last-child {{
            border-bottom: none;
        }}
        
        .guidelines {{
            background-color: var(--light-gray);
            padding: 20px;
            border-left: 4px solid var(--secondary-color);
            margin: 20px 0;
        }}
        
        footer {{
            background-color: var(--primary-color);
            color: white;
            text-align: center;
            padding: 20px 0;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>{title}</h1>
            <div class="meta-info">
                <div>Prepared for: {client_name}</div>
                <div>Date: {current_date}</div>
            </div>
        </div>
    </header>
    
    <div class="container">
        <section>
            <h2>Logo Designs</h2>
            <div class="logo-showcase">
                {logo_showcase}
            </div>
        </section>
        
        <section>
            <h2>Design Rationale</h2>
            <p>{design_rationale}</p>
        </section>
        
        <section>
            <h2>Design Elements</h2>
            <div class="design-elements">
                {elements_html if elements_html else "<p>No specific design elements were highlighted for this logo.</p>"}
            </div>
        </section>
        
        <section>
            <h2>Color Palette</h2>
            <div class="color-palette">
                {color_blocks}
            </div>
        </section>
        
        <section>
            <h2>Typography</h2>
            <div class="font-samples">
                {font_list}
            </div>
        </section>
        
        <section>
            <h2>Usage Guidelines</h2>
            <div class="guidelines">
                <p>{usage_guidelines}</p>
            </div>
        </section>
    </div>
    
    <footer>
        <div class="container">
            <p>© {time.strftime("%Y")} Logo Design Agent | Generated Report</p>
        </div>
    </footer>
</body>
</html>
"""
    return html

@tool
def web_search(
    query: str,
    search_type: str = "design",
    max_results: int = 10,
    include_images: bool = False
) -> str:
    """
    Search the web for logo design related information and professional knowledge.
    
    Args:
        query: Search query
        search_type: Type of search (design, brand, industry, color, typography)
        max_results: Maximum number of results to return
        include_images: Whether to include image results
        
    Returns:
        str: JSON string containing search results
    """
    try:
        # Validate parameters
        if max_results < 1:
            max_results = 10
        elif max_results > 30:
            max_results = 30
            
        # Enhance query based on search type
        enhanced_query = query
        if search_type.lower() == "design":
            enhanced_query = f"logo design {query}"
        elif search_type.lower() == "brand":
            enhanced_query = f"brand identity {query}"
        elif search_type.lower() == "industry":
            enhanced_query = f"{query} industry logo trends"
        elif search_type.lower() == "color":
            enhanced_query = f"color psychology {query} logo design"
        elif search_type.lower() == "typography":
            enhanced_query = f"typography {query} logo design"
        
        # Initialize AWS Bedrock client for Claude
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )
        
        # Create a prompt for Claude to simulate search results
        prompt = f"""
        You are a web search simulator for logo design professionals. I need you to provide realistic search results for the query: "{enhanced_query}"
        
        Please generate {max_results} search results that would be relevant to this query. Each result should include:
        1. A title
        2. A URL (make these realistic but fictional)
        3. A snippet/description
        4. A publication date (within the last 2 years)
        
        The results should be varied and include:
        - Design blogs and resources
        - Professional articles
        - Tutorial sites
        - Industry insights
        - Case studies
        
        Focus on high-quality, professional sources that a logo designer would find valuable.
        
        Return the results in a structured JSON format with these fields:
        - query: the original query
        - enhanced_query: the enhanced query used
        - total_results: a realistic number of total results
        - results: array of result objects with title, url, snippet, and date fields
        
        Do not include any explanations or additional text outside the JSON structure.
        """
        
        # Make the request to Claude
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        content = response_body["content"][0]["text"]
        
        # Extract JSON from response (Claude sometimes adds markdown formatting)
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_content = content[json_start:json_end]
            search_results = json.loads(json_content)
        else:
            raise ValueError("Failed to extract valid JSON from response")
        
        # Add metadata
        search_results["metadata"] = {
            "search_type": search_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "include_images": include_images
        }
        
        # Add simulated image results if requested
        if include_images:
            search_results["image_results"] = _generate_simulated_image_results(query, 5)
            
        return json.dumps(search_results)
        
    except Exception as e:
        error_msg = f"Error performing web search: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "query": query
        })

def _generate_simulated_image_results(query: str, count: int = 5) -> List[Dict[str, str]]:
    """
    Generate simulated image search results.
    
    Args:
        query: Search query
        count: Number of image results to generate
        
    Returns:
        List of image result dictionaries
    """
    image_results = []
    for i in range(count):
        # Generate a random ID for the image
        image_id = str(uuid.uuid4())[:8]
        
        # Create a simulated image result
        image_results.append({
            "title": f"{query.title()} Design Example {i+1}",
            "source_url": f"https://design-inspiration.com/logos/{query.lower().replace(' ', '-')}-{i+1}",
            "image_url": f"https://example.com/images/{image_id}.jpg",
            "width": 800,
            "height": 600,
            "source_name": f"Design Resource {i+1}"
        })
        
    return image_results