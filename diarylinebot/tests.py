from django.test import TestCase

# Create your tests here.
document = [
    "The extractive summarization feature uses natural language processing techniques to locate key sentences in an unstructured text document. "
    "These sentences collectively convey the main idea of the document. This feature is provided as an API for developers. " 
    "They can use it to build intelligent solutions based on the relevant information extracted to support various use cases. "
    "In the public preview, extractive summarization supports several languages. It is based on pretrained multilingual transformer models, part of our quest for holistic representations. "
    "It draws its strength from transfer learning across monolingual and harness the shared nature of languages to produce models of improved quality and efficiency. "
]
print(len(document))