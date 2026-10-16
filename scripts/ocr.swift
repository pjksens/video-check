// OCR des images d'un dossier avec Vision (macOS) → JSON [{f, items:[{t,x,y,w,h}]}], coordonnées normalisées, origine en haut à gauche.
import AppKit
import Foundation
import Vision

let dir = CommandLine.arguments[1]
let files = (try? FileManager.default.contentsOfDirectory(atPath: dir).filter { $0.hasSuffix(".jpg") }.sorted()) ?? []
var out: [[String: Any]] = []
for f in files {
    let url = URL(fileURLWithPath: dir).appendingPathComponent(f)
    guard let img = NSImage(contentsOf: url), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["fr-FR", "en-US"]
    req.usesLanguageCorrection = false
    req.minimumTextHeight = 0.015
    try? VNImageRequestHandler(cgImage: cg).perform([req])
    var items: [[String: Any]] = []
    for o in req.results ?? [] {
        guard let c = o.topCandidates(1).first, c.confidence >= 0.5 else { continue }
        let b = o.boundingBox
        items.append(["t": c.string, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height])
    }
    out.append(["f": f, "items": items])
}
let data = try JSONSerialization.data(withJSONObject: out)
FileHandle.standardOutput.write(data)
